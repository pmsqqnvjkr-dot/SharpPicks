const ORIGIN = 'https://app.sharppicks.ai';

export async function proxyToOrigin(context) {
  const url = new URL(context.request.url);
  const originUrl = `${ORIGIN}${url.pathname}${url.search}`;

  try {
    const response = await fetch(originUrl, {
      method: context.request.method,
      headers: {
        'User-Agent': context.request.headers.get('User-Agent') || 'SharpPicks-Proxy',
        'Accept': context.request.headers.get('Accept') || '*/*',
        'X-Forwarded-Host': url.hostname,
        'X-Forwarded-Proto': 'https',
      },
    });

    const newHeaders = new Headers(response.headers);
    newHeaders.delete('x-frame-options');

    const linkHeader = newHeaders.get('link');
    if (linkHeader) {
      newHeaders.set('link', linkHeader.replace(/app\.sharppicks\.ai/g, 'sharppicks.ai'));
    }

    return new Response(response.body, {
      status: response.status,
      headers: newHeaders,
    });
  } catch (error) {
    return new Response('Origin unavailable', { status: 502 });
  }
}
