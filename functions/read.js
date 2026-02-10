export async function onRequestGet(context) {
    try {
        // 从 KV 读取 connection 值
        const value = await context.env.connection.get('connection');
        
        // 返回响应
        return new Response(JSON.stringify({
            success: true,
            value: value
        }), {
            headers: { 'Content-Type': 'application/json' }
        });
        
    } catch (error) {
        return new Response(JSON.stringify({
            success: false,
            error: error.message
        }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}