export async function onRequestPost(context) {
    try {
        // 获取请求数据
        //const { value } = await context.request.json();
        const value=await context.request.get("value");
        // 写入 KV（键名: connection）
        await context.env.connection.put('connection', value);
        
        // 返回成功响应
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