function read_connect(cncs){
    let ans=cncs.split(";");
    let anss={};
    for (var i = 0; i <ans.length-1; i++) {
        anss[ans[i]["id"]]=ans[i]["last-time"]
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
        const req = await context.request.json();
        const id=req["id"];
        const time=req["time"];

        const st = await context.env.store.get('connection');
        let stj=read_connect(st);

        stj[id]=time;

        let cns=write_connect(stj);
        await context.env.store.put('connection', cns);
        //const value = await context.env.store.get('connection');
        
        // 返回响应
        return new Response(JSON.stringify({
            success: true,
            st:st,
            stj:stj,
            cns: cns
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