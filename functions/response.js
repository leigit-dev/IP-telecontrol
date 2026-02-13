export async function onRequestPost(context) {
    try {
        const req = await context.request.json();

        // const ssn = await context.env.command.get('session');
        // if(req["session"] != ssn){
        //     return new Response(JSON.stringify({
        //         success:true,
        //         access:false
        //         }), {
        //             headers: { 'Content-Type': 'application/json' }
        //     });
        // }

        const reshead=req["head"];
        const resbody=req["body"];
        const id=req["id"];

        await context.env.response.put('head', reshead);
        await context.env.response.put('body', resbody);
        await context.env.command.put('receiver-situ', id+"|FINISHED");

        return new Response(JSON.stringify({
            success:true,
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