export async function onRequestPost(context) {
    try {
        const req = await context.request.json();
        

        const resi = await context.env.command.get('receiver-situ');
        const [receiver,situ]=resi.split("|");
        await context.env.command.put('receiver-situ', "anyone|CANCELLED");
        
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