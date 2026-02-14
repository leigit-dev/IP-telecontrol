function read_connect(cncs){
    let ans=cncs.split(";");
    let anss={};
    for (var i = 0; i <ans.length-1; i++) {
        anss[ans[i].split(":")[0]]=ans[i].split(":")[1];
    }
    return anss;
}

function write_connect(cncs){
    let ans="";
    for (let k in cncs) {
        ans=ans+k+":"+cncs[k]+";";
        //anss[ans[i]["id"]]=ans[i]["last-time"]
    }
    return ans;
}
export async function onRequestPost(context) {
    try {
        const st = await context.env.connects.get('connection');
        let stj=read_connect(st);
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