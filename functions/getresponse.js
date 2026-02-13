export async function onRequestPost(context) {
    try {

        // const ssn = await context.env.command.get('session');
        // if(req["session"] != ssn){
        //     return new Response(JSON.stringify({
        //         success:true,
        //         access:false
        //         }), {
        //             headers: { 'Content-Type': 'application/json' }
        //     });
        // }

        const situ = await context.env.command.get('receiver-situ');
        // await context.env.response.put('head', reshead);
        // await context.env.response.put('body', resbody);
        // await context.env.command.put('situation', "FINISHED");
        let {receiver,stat} = situ.split("|");
        if(stat=="FINISHED"){
            const rshead = await context.env.response.get('head');
            const rsbody = await context.env.response.get("body");
            return new Response(JSON.stringify({
                success:true,
                situation:situ,
                rshead:rshead,
                rsbody:rsbody
                }), {
                    headers: { 'Content-Type': 'application/json' }
            });
        }
        else{
            return new Response(JSON.stringify({
                success:true,
                situation:situ
                }), {
                    headers: { 'Content-Type': 'application/json' }
            });
        }
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