export async function onRequestPost(context) {
    try {
        const req = await context.request.json();

        const ssn = await context.env.command.get('session');
        if(req["session"] != ssn){
            return new Response(JSON.stringify({
                success:true,
                access:false
                }), {
                    headers: { 'Content-Type': 'application/json' }
            });
        }

        const receiver=req["receiver"];
        const cmd=req["cmd"];

        await context.env.command.put('receiver', receiver);
        await context.env.command.put('cmd', cmd);
        await context.env.command.put('situation', "PENDING");

        return new Response(JSON.stringify({
            success:true,
            access:true
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