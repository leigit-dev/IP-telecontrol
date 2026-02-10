// functions/hello.js
export async function onRequestGet(context) {
  // context 包含 request, env 等信息[citation:2]
  return new Response('Hello from Pages Function!');
}