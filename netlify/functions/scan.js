exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: { Allow: 'POST' }, body: JSON.stringify({ error: 'Method not allowed' }) };
  const token = process.env.GITHUB_TOKEN;
  if (!token) return { statusCode: 503, body: JSON.stringify({ error: 'Brak GITHUB_TOKEN w zmiennych środowiskowych Netlify.' }) };
  try {
    const response = await fetch('https://api.github.com/repos/racibo/gdansk/actions/workflows/monitor.yml/dispatches', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
      body: JSON.stringify({ ref: 'main' })
    });
    if (!response.ok) return { statusCode: response.status, body: JSON.stringify({ error: 'GitHub API: ' + (await response.text()).slice(0, 300) }) };
    return { statusCode: 202, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }, body: JSON.stringify({ ok: true }) };
  } catch (error) { return { statusCode: 500, body: JSON.stringify({ error: error.message }) }; }
};