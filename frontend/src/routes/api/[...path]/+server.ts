import type { RequestHandler } from './$types';

const SSR_API_BASE_URL = process.env.SSR_API_BASE_URL || 'http://backend:8080';

const HOP_BY_HOP_HEADERS = [
	'connection',
	'keep-alive',
	'proxy-authenticate',
	'proxy-authorization',
	'te',
	'trailers',
	'transfer-encoding',
	'upgrade',
	'host'
];

async function proxy(request: Request, params: { path: string }, url: URL): Promise<Response> {
	const targetUrl = new URL(`${params.path}${url.search}`, SSR_API_BASE_URL);

	const headers = new Headers(request.headers);
	for (const name of HOP_BY_HOP_HEADERS) {
		headers.delete(name);
	}

	const shouldHaveBody = request.method !== 'GET' && request.method !== 'HEAD';
	const body = shouldHaveBody ? await request.arrayBuffer() : undefined;

	const response = await fetch(targetUrl.toString(), {
		method: request.method,
		headers,
		body
	});

	const responseHeaders = new Headers(response.headers);
	for (const name of HOP_BY_HOP_HEADERS) {
		responseHeaders.delete(name);
	}

	return new Response(response.body, {
		status: response.status,
		statusText: response.statusText,
		headers: responseHeaders
	});
}

export const GET: RequestHandler = async ({ request, params, url }) => proxy(request, params, url);
export const POST: RequestHandler = async ({ request, params, url }) => proxy(request, params, url);
export const PUT: RequestHandler = async ({ request, params, url }) => proxy(request, params, url);
export const PATCH: RequestHandler = async ({ request, params, url }) =>
	proxy(request, params, url);
export const DELETE: RequestHandler = async ({ request, params, url }) =>
	proxy(request, params, url);
export const OPTIONS: RequestHandler = async ({ request, params, url }) =>
	proxy(request, params, url);
