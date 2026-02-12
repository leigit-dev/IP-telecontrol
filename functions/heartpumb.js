export async function onRequestPost(context) {
    try {
        const req = await context.request.json();
        const id=req["id"];

        const receiver = await context.env.command.get('receiver');

        if(id==receiver || receiver=="*"){
            const cmd=await context.env.command.get('cmd');
            return new Response(JSON.stringify({
                success:true,
                isme: true,
                cmd:cmd

                }), {
                    headers: { 'Content-Type': 'application/json' }
            });

        }
        else{
            return new Response(JSON.stringify({
                success:true,
                isme: false,

                }), {
                    headers: { 'Content-Type': 'application/json' }
            });
        }
        // stj[id]=time;

        // let cns=write_connect(stj);
        // await context.env.command.put('connection', cns);
        // //const value = await context.env.store.get('connection');
        
        // const 
        // 返回响应
        
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