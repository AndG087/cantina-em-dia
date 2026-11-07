export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    signal: options?.signal ?? AbortSignal.timeout(7000),
  });
  if (!response.ok) {
    let message = 'Não foi possível concluir. Verifique se o sistema está iniciado.';
    try {
      const error = await response.json();
      if (typeof error.detail === 'string') message = error.detail;
      else if (Array.isArray(error.detail)) message = 'Revise os campos informados e tente novamente.';
    } catch { /* A resposta pode ser do proxy, em vez da API. */ }
    throw new Error(message);
  }
  return response.json();
}

export type AppSettings = {
  business_name: string; location: string; manager_name: string;
  timezone: 'America/Sao_Paulo'; updated_at: string;
};
export type DatabaseHealth = {
  status: string; database: string; engine: string;
  migration: string; server_version: string; checked_at: string;
};
export type DocumentInfo = { id: string; title: string; filename: string; description: string };
