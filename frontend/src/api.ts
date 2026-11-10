export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options?.headers }, signal: options?.signal ?? AbortSignal.timeout(10000) });
  if (!response.ok) {
    let message = 'Não foi possível concluir. Verifique se o sistema está iniciado.';
    try {
      const error = await response.json();
      if (typeof error.detail === 'string') message = error.detail;
      else if (Array.isArray(error.detail)) message = 'Revise os campos informados e tente novamente.';
    } catch { /* A resposta pode não ser da API. */ }
    throw new Error(message);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}
