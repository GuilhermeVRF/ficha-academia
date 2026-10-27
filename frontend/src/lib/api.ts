/** HTTP status error returned by the API. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

/** The request never reached the server (offline, DNS, timeout...). */
export class NetworkError extends Error {}

export async function request<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method,
      credentials: 'same-origin',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    throw new NetworkError(String(error))
  }
  if (!response.ok) {
    const detail = await response
      .json()
      .then((data) => (typeof data?.detail === 'string' ? data.detail : response.statusText))
      .catch(() => response.statusText)
    throw new ApiError(response.status, detail)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}
