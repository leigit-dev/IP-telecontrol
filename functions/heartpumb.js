export async function onRequestPost(context) {
    try {
        const req = await context.request.json();
        const id=req["id"];

        const st = await context.env.command.get('receiver');
        let stj=read_connect(st);

        // stj[id]=time;

        // let cns=write_connect(stj);
        // await context.env.command.put('connection', cns);
        // //const value = await context.env.store.get('connection');
        
        // const 
        // 返回响应
        return new Response(JSON.stringify({
            success: true,
            
            stj:stj
            
        }), {
            headers: { 'Content-Type': 'application/json' }
        });
    } 
    catch (error) {
        return new Response(JSON.stringify({
            success: false,
            error: error.message
        }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}