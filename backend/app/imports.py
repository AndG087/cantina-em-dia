import csv
import hashlib
import io
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field, ValidationError, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .domain import TZ, audit, aware, get_or_404, lock, rows
from .finance import SaleIn, SaleLineIn, SalePaymentIn, SettlementIn, create_sale_record, record_settlement, cash_session, add_cash_entry
from .inventory import ItemIn, MovementIn, change_stock
from .models import ImportBatch, ImportRow, StockItem, Sale, SalePayment
from .team import Input

router = APIRouter(prefix='/api', tags=['Importações'])
DB = Annotated[Session, Depends(get_session)]
KINDS = {
    'items': {'label': 'Cadastro de produtos e insumos', 'required': ['sku', 'name', 'category', 'kind', 'unit'], 'optional': ['minimum', 'unit_cost', 'sale_price', 'price_locked', 'price_source']},
    'sales_summary': {'label': 'Resumo financeiro de vendas (sem baixa de estoque)', 'required': ['external_id', 'occurred_at', 'method', 'amount'], 'optional': []},
    'sales_items': {'label': 'Vendas por produto (com baixa de estoque)', 'required': ['external_id', 'occurred_at', 'method', 'sku', 'quantity', 'unit_price'], 'optional': ['discount']},
    'settlements': {'label': 'Recebimentos digitais para conciliação', 'required': ['external_id', 'method', 'gross', 'fee', 'occurred_at', 'reference'], 'optional': []},
    'initial_stock': {'label': 'Saldos iniciais por lote', 'required': ['external_id', 'sku', 'quantity', 'occurred_at'], 'optional': ['unit_cost', 'lot_code', 'expiry']},
}
LABELS = {'sku': 'Código / SKU', 'name': 'Nome', 'category': 'Categoria', 'kind': 'Tipo: product, ingredient, packaging', 'unit': 'Unidade: un, kg, L', 'minimum': 'Estoque mínimo', 'unit_cost': 'Custo por unidade em R$', 'sale_price': 'Preço de venda em R$', 'price_locked': 'Preço fixo: sim/não', 'price_source': 'Origem do preço', 'external_id': 'Referência externa única', 'occurred_at': 'Data e hora em Brasília', 'method': 'Dinheiro, Pix, débito ou crédito', 'amount': 'Venda antes das taxas (R$)', 'quantity': 'Quantidade na unidade cadastrada', 'unit_price': 'Preço por unidade vendido (R$)', 'discount': 'Desconto total do registro (R$)', 'gross': 'Bruto recebido (R$)', 'fee': 'Taxa efetiva (R$), inclusive zero', 'reference': 'Referência única do recebimento', 'lot_code': 'Lote', 'expiry': 'Validade'}


class CsvIn(Input):
    model_config = ConfigDict(str_strip_whitespace=False, extra='forbid')
    content: str = Field(min_length=1, max_length=2_000_000)


class ImportIn(CsvIn):
    kind: Literal['items', 'sales_summary', 'sales_items', 'settlements', 'initial_stock']
    filename: str = Field(default='arquivo.csv', max_length=150)
    mapping: dict[str, str] = Field(default_factory=dict)
    cash_session_id: int | None = None


class CommitIn(ImportIn):
    expected_hash: str = Field(min_length=64, max_length=64)


def csv_rows(content):
    text = content.lstrip('\ufeff')
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=';,\t')
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text), delimiter=';')
    headers = reader.fieldnames or []
    if not headers or len(headers) != len(set(headers)):
        raise HTTPException(422, 'O CSV precisa de um cabeçalho com nomes de colunas únicos.')
    parsed = []
    try:
        for row in reader:
            if None in row:
                raise HTTPException(422, 'Número de colunas inconsistente. Confira o delimitador do CSV.')
            if any((value or '').strip() for value in row.values()):
                parsed.append(row)
                if len(parsed) > 2000:
                    raise HTTPException(422, 'Importe até 2.000 linhas de cada vez.')
    except csv.Error:
        raise HTTPException(422, 'CSV inválido.')
    if not parsed:
        raise HTTPException(422, 'O arquivo não contém registros.')
    return headers, parsed


def decimal_value(value):
    raw = str(value).replace('R$', '').replace(' ', '').strip()
    if ',' in raw and '.' in raw:
        if raw.rfind(',') > raw.rfind('.'):
            raw = raw.replace('.', '').replace(',', '.')
        else:
            raw = raw.replace(',', '')
    else:
        raw = raw.replace(',', '.')
    try:
        result = Decimal(raw)
        if not result.is_finite(): raise InvalidOperation()
        return result
    except InvalidOperation:
        raise ValueError('Valor numérico inválido.')


def money_value(value):
    amount = decimal_value(value)
    if amount < 0 or amount * 100 != (amount * 100).to_integral_value() or amount > Decimal('20000000'):
        raise ValueError('Valor monetário deve ser não negativo e ter até duas casas decimais.')
    return int(amount * 100)


def csv_time(value):
    raw = str(value).strip()
    try: result = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        result = None
        for fmt in ['%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y']:
            try: result = datetime.strptime(raw, fmt); break
            except ValueError: pass
        if result is None: raise ValueError('Data inválida. Use data e hora em Brasília ou ISO com fuso.')
    return aware(result.replace(tzinfo=TZ) if result.tzinfo is None else result)


def csv_date(value):
    raw = str(value).strip()
    for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
        try: return datetime.strptime(raw, fmt).date()
        except ValueError: pass
    raise ValueError('Validade inválida. Use AAAA-MM-DD ou DD/MM/AAAA.')


def method(value):
    raw = ''.join(c for c in unicodedata.normalize('NFD', value.lower()) if unicodedata.category(c) != 'Mn').strip()
    methods = {'dinheiro': 'cash', 'cash': 'cash', 'pix': 'pix', 'debito': 'debit', 'debit': 'debit', 'cartao de debito': 'debit', 'credito': 'credit', 'credit': 'credit', 'cartao de credito': 'credit'}
    if raw not in methods: raise ValueError('Forma de pagamento não reconhecida.')
    return methods[raw]


def prepare(data):
    headers, parsed = csv_rows(data.content)
    fields = KINDS[data.kind]
    mapping = {field: data.mapping.get(field, field) for field in fields['required'] + fields['optional']}
    missing = [LABELS[field] for field in fields['required'] if mapping[field] not in headers]
    if missing: raise HTTPException(422, 'Mapeie as colunas obrigatórias: ' + ', '.join(missing))
    result = [{field: (row.get(header) or '').strip() if header in headers else '' for field, header in mapping.items()} for row in parsed]
    return result, hashlib.sha256(data.content.encode('utf-8')).hexdigest()


def import_records(data, db):
    normalized, digest = prepare(data); lock(db, 801)
    if db.scalar(select(ImportBatch.id).where(ImportBatch.kind == data.kind, ImportBatch.file_hash == digest)):
        raise HTTPException(409, 'Este arquivo já foi importado para esse tipo de registro.')
    batch = ImportBatch(kind=data.kind, filename=data.filename, file_hash=digest, row_count=len(normalized), mapping=data.mapping, raw_csv=data.content)
    db.add(batch); db.flush()
    for number, record in enumerate(normalized, 2):
        try:
            external = record['reference'] if data.kind == 'settlements' else record.get('external_id') or record.get('sku')
            if not external or len(external) > 150:
                raise ValueError('A referência externa é obrigatória e deve ter até 150 caracteres.')
            if db.scalar(select(ImportRow.id).where(ImportRow.kind == data.kind, ImportRow.external_reference == external)):
                raise HTTPException(409, 'Referência externa já importada.')
            if data.kind == 'items':
                if db.scalar(select(StockItem.id).where(StockItem.sku == record['sku'])):
                    raise HTTPException(409, 'SKU já cadastrado. A importação não sobrescreve cadastros.')
                flag = record['price_locked'].lower()
                if flag not in {'', 'sim', 'não', 'nao', 'true', 'false', '1', '0'}:
                    raise ValueError('Preço fixo deve ser sim ou não.')
                item_data = ItemIn(sku=record['sku'], name=record['name'], category=record['category'], kind=record['kind'], unit=record['unit'], minimum=decimal_value(record['minimum'] or '0'),
                                   unit_cost_cents=money_value(record['unit_cost'] or '0'), sale_price_cents=money_value(record['sale_price']) if record['sale_price'] else None,
                                   price_locked=flag in {'sim', 'true', '1'}, price_source=record['price_source'], cost_known=bool(record['unit_cost']))
                entity = StockItem(**item_data.model_dump()); db.add(entity); db.flush(); key = entity.id
            elif data.kind in {'sales_summary', 'sales_items'}:
                instant = csv_time(record['occurred_at']); payment_method = method(record['method'])
                if db.scalar(select(Sale.id).where(Sale.external_id == external)):
                    raise HTTPException(409, 'Referência de venda já registrada.')
                if data.kind == 'sales_items':
                    item = db.scalar(select(StockItem).where(StockItem.sku == record['sku']))
                    if item is None: raise ValueError('SKU não encontrado. Cadastre o produto antes.')
                    qty = decimal_value(record['quantity']); price = money_value(record['unit_price']); discount = money_value(record['discount'] or '0')
                    amount = int((qty * price).quantize(Decimal(1), rounding=ROUND_HALF_UP)) - discount
                    sale = create_sale_record(db, SaleIn(occurred_at=instant, cash_session_id=data.cash_session_id, external_id=external, note=f'Importado de {data.filename}', discount_cents=discount,
                        lines=[SaleLineIn(item_id=item.id, quantity=qty, unit_price_cents=price)], payments=[SalePaymentIn(method=payment_method, amount_cents=amount)]))
                else:
                    amount = money_value(record['amount'])
                    if amount <= 0: raise ValueError('A venda precisa de valor positivo.')
                    session = cash_session(db, data.cash_session_id) if payment_method == 'cash' and data.cash_session_id is not None else None
                    if payment_method == 'cash' and session is None: raise ValueError('Selecione o caixa aberto para importar dinheiro.')
                    sale = Sale(occurred_at=instant, total_cents=amount, discount_cents=0, cost_cents=0, cost_known=False, stock_applied=False, cashier_id=session.employee_id if session else None, external_id=external, note=f'Resumo financeiro sem itens: {data.filename}')
                    db.add(sale); db.flush(); payment = SalePayment(sale_id=sale.id, method=payment_method, amount_cents=amount); db.add(payment); db.flush()
                    if session:
                        add_cash_entry(db, session.id, 'sale', amount, instant, f'Venda importada #{sale.id}', f'sale_payment:{payment.id}')
                key = sale.id
            elif data.kind == 'settlements':
                sale = db.scalar(select(Sale).where(Sale.external_id == record['external_id']))
                if not sale: raise ValueError('Referência externa da venda não encontrada.')
                choices = db.scalars(select(SalePayment).where(SalePayment.sale_id == sale.id, SalePayment.method == method(record['method']))).all()
                if len(choices) != 1: raise ValueError('Não foi possível identificar um único pagamento da venda.')
                settlement = record_settlement(db, SettlementIn(payment_id=choices[0].id, gross_cents=money_value(record['gross']), fee_cents=money_value(record['fee']), occurred_at=csv_time(record['occurred_at']), reference=record['reference']))
                key = settlement.id; external = record['reference']
            else:
                item = db.scalar(select(StockItem).where(StockItem.sku == record['sku']))
                if item is None: raise ValueError('SKU não encontrado.')
                qty = decimal_value(record['quantity'])
                if qty <= 0: raise ValueError('Quantidade deve ser positiva.')
                movement = MovementIn(item_id=item.id, quantity=qty, kind='opening', reason=f'Saldo inicial importado · {external}', occurred_at=csv_time(record['occurred_at']),
                                      lot_code=record['lot_code'], expiry=csv_date(record['expiry']) if record['expiry'] else None, unit_cost_cents=money_value(record['unit_cost']) if record['unit_cost'] else None)
                moved = change_stock(db, item.id, movement.quantity, 'opening', movement.reason, movement.occurred_at, lot_code=movement.lot_code, expiry=movement.expiry,
                                     unit_cost_cents=movement.unit_cost_cents, reference_type='import', reference_id=batch.id)
                key = moved[0].id
            db.add(ImportRow(batch_id=batch.id, kind=data.kind, external_reference=external, entity_id=key)); db.flush()
        except HTTPException as error:
            raise HTTPException(error.status_code, f'Linha {number}: {error.detail}')
        except ValidationError as error:
            first = error.errors()[0]
            raise HTTPException(422, f"Linha {number}, campo {'.'.join(str(p) for p in first['loc'])}: {first['msg']}")
        except (ValueError, KeyError) as error:
            message = str(error).split('\n')[0]
            raise HTTPException(422, f'Linha {number}: {message}')
    audit(db, 'import', batch.id, 'committed', {'kind': data.kind, 'filename': data.filename, 'rows': len(normalized), 'sha256': digest})
    return batch, normalized


@router.get('/imports/config')
def config():
    return {'kinds': KINDS, 'labels': LABELS}


@router.post('/imports/inspect')
def inspect_csv(data: CsvIn):
    headers, parsed = csv_rows(data.content)
    return {'headers': headers, 'row_count': len(parsed), 'sample': parsed[:3]}


@router.post('/imports/preview')
def preview(data: ImportIn, db: DB):
    nested = db.begin_nested()
    try:
        batch, normalized = import_records(data, db)
        result = {'row_count': len(normalized), 'sha256': batch.file_hash, 'sample': normalized[:10], 'kind': data.kind}
    finally:
        nested.rollback()
    return result


@router.post('/imports/commit', status_code=201)
def commit(data: CommitIn, db: DB):
    if hashlib.sha256(data.content.encode('utf-8')).hexdigest() != data.expected_hash:
        raise HTTPException(409, 'O arquivo mudou depois da prévia. Valide novamente.')
    batch, normalized = import_records(data, db); db.commit()
    return {'id': batch.id, 'row_count': len(normalized), 'sha256': batch.file_hash}


@router.get('/imports')
def history(db: DB):
    return [{'id': b.id, 'kind': b.kind, 'filename': b.filename, 'file_hash': b.file_hash, 'row_count': b.row_count, 'recorded_at': b.recorded_at} for b in rows(db, ImportBatch)]


@router.get('/imports/{key}/source')
def source(key: int, db: DB):
    batch = get_or_404(db, ImportBatch, key)
    return Response(batch.raw_csv, media_type='text/plain; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="origem-importacao-{key}.txt"'})


@router.get('/imports/template/{kind}')
def template(kind: str):
    if kind not in KINDS: raise HTTPException(404, 'Modelo não encontrado.')
    stream = io.StringIO(); writer = csv.writer(stream, delimiter=';'); writer.writerow(KINDS[kind]['required'] + KINDS[kind]['optional'])
    return Response('\ufeff' + stream.getvalue(), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="modelo-{kind}.csv"'})
