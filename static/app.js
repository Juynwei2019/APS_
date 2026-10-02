let data, tab = 'resources', dirty = false;
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statusNames = {on_time:'準時',late:'逾期',unscheduled:'未排入'};
function message(text, error=false) { $('message').textContent=text; $('message').className=error?'error':''; }
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '請求失敗');
  return result;
}
function field(title, key, value, type='text', extra='') { return `<label>${title}<input data-key="${key}" type="${type}" value="${esc(value)}" ${extra}></label>`; }
function options(items, value) { return `<option value="">請選擇</option>` + items.map(x=>`<option value="${esc(x.id)}" ${x.id===value?'selected':''}>${esc(x.id)} · ${esc(x.name || x.id)}</option>`).join(''); }
function select(title,key,items,value) { return `<label>${title}<select data-key="${key}">${options(items,value)}</select></label>`; }
function renderEditor() {
  $('editor').innerHTML = data[tab].map((item,index)=>{
    let content=field('識別碼','id',item.id);
    if(tab==='orders') content+=select('產品','product',data.products,item.product)+field('數量','quantity',item.quantity,'number','min="1" step="1"')+field('優先順序（1 最高）','priority',item.priority,'number','min="1" max="9" step="1"')+field('交期','due',item.due,'datetime-local');
    else content+=field('名稱','name',item.name);
    content+=`<button class="delete" data-action="delete">刪除</button>`;
    let children='';
    if(tab==='resources') children=item.windows.map((w,i)=>`<div class="subrow" data-child="${i}">${field('可用開始','start',w.start,'datetime-local')}${field('可用結束','end',w.end,'datetime-local')}<button class="delete" data-action="remove-child">移除時段</button></div>`).join('');
    if(tab==='products') children=item.route.map((op,i)=>`<div class="subrow" data-child="${i}">${field(`工序 ${i+1} 名稱`,'name',op.name)}${select('設備','resource',data.resources,op.resource)}${field('單件加工分鐘','minutes_per_unit',op.minutes_per_unit,'number','min="1" step="1"')}<button class="delete" data-action="remove-child">移除工序</button></div>`).join('');
    return `<div class="card" data-index="${index}"><div class="fields">${content}</div>${children}${tab!=='orders'?`<button class="secondary small" data-action="add-child">＋ ${tab==='resources'?'可用時段':'下一道工序'}</button>`:''}</div>`;
  }).join('') || '<p class="empty">尚無資料，點擊「新增」開始建立。</p>';
}
function changed() {dirty=true; $('results').hidden=true; message('資料已修改，請儲存後重新排程。');}
$('editor').addEventListener('input', e=>{
  const input=e.target, card=input.closest('[data-index]'); if(!card || !input.dataset.key) return;
  let item=data[tab][Number(card.dataset.index)];
  const child=input.closest('[data-child]');
  if(child) item=(tab==='resources'?item.windows:item.route)[Number(child.dataset.child)];
  item[input.dataset.key]=input.type==='number'?Number(input.value):input.value;
  changed();
});
$('editor').addEventListener('click',e=>{
  const action=e.target.dataset.action, card=e.target.closest('[data-index]'); if(!action || !card)return;
  const index=Number(card.dataset.index), item=data[tab][index];
  if(action==='delete') data[tab].splice(index,1);
  else {const children=tab==='resources'?item.windows:item.route;
    if(action==='remove-child') children.splice(Number(e.target.closest('[data-child]').dataset.child),1);
    else children.push(tab==='resources'?{start:$('start').value,end:$('end').value}:{name:'新工序',resource:data.resources[0]?.id||'',minutes_per_unit:10});
  }
  changed();renderEditor();
});
document.querySelectorAll('.tab').forEach(button=>button.onclick=()=>{tab=button.dataset.tab;document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b===button));renderEditor();});
$('add').onclick=()=>{data[tab].push(tab==='resources'?{id:'',name:'',windows:[]}:tab==='products'?{id:'',name:'',route:[]}:{id:'',product:data.products[0]?.id||'',quantity:1,priority:1,due:$('end').value});changed();renderEditor();};
$('save').onclick=async()=>{try{await api('/api/data',data);dirty=false;message('資料已儲存。現在可以產生排程。');}catch(e){message(e.message,true);}};
$('sample').onclick=async()=>{if(!confirm('載入範例將取代畫面上的資料，需按儲存才會覆寫資料庫。繼續？'))return;try{data=await api('/api/sample');changed();renderEditor();}catch(e){message(e.message,true);}};
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='aps-data.json';a.click();URL.revokeObjectURL(url);};
function table(headers,rows){return `<table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`;}
const dateText = value => value?value.replace('T',' '):'—';
const badge = status=>`<span class="badge ${status}">${statusNames[status]}</span>`;
function renderResult(result,start,end) {
  $('results').hidden=false;
  $('stats').innerHTML=[['訂單總數',result.orders.length],['準時完成',result.orders.filter(o=>o.status==='on_time').length],['逾期訂單',result.orders.filter(o=>o.status==='late').length],['未排入訂單',result.orders.filter(o=>o.status==='unscheduled').length]].map(([name,n])=>`<div class="stat">${name}<strong>${n}</strong></div>`).join('');
  $('summary').innerHTML=table(['訂單','交期','預計完工','狀態'],result.orders.map(o=>`<tr><td>${esc(o.order)}</td><td>${esc(dateText(o.due))}</td><td>${esc(dateText(o.completion))}</td><td>${badge(o.status)}</td></tr>`));
  $('operations').innerHTML=table(['訂單','工序','設備','加工分鐘','開始','結束','結果'],result.operations.map(op=>`<tr><td>${esc(op.order)}</td><td>${op.sequence}. ${esc(op.operation)}</td><td>${esc(op.resource)}</td><td>${op.duration}</td><td>${esc(dateText(op.start))}</td><td>${esc(dateText(op.end))}</td><td>${op.status==='scheduled'?'已排入':esc(op.reason)}</td></tr>`));
  const from=new Date(start).getTime(),span=new Date(end).getTime()-from;
  $('gantt').innerHTML=`<div class="axis"><span>${esc(dateText(start))}</span><span>${esc(dateText(end))}</span></div>`+data.resources.map(r=>`<div class="gantt-row"><div class="gantt-name">${esc(r.name || r.id)}</div><div class="track">${result.operations.filter(o=>o.resource===r.id&&o.status==='scheduled').map(o=>{
    const left=(new Date(o.start).getTime()-from)/span*100,width=(new Date(o.end).getTime()-new Date(o.start).getTime())/span*100;
    return `<div class="bar ${data.orders.findIndex(x=>x.id===o.order)%2?'alt':''}" style="left:${left}%;width:${width}%" title="${esc(`${o.order} · ${o.operation} · ${dateText(o.start)} → ${dateText(o.end)}`)}">${esc(o.order)}</div>`;
  }).join('')}</div></div>`).join('');
}
$('run').onclick=async()=>{if(dirty){message('請先儲存資料，再產生排程。',true);return;}const start=$('start').value,end=$('end').value;$('run').disabled=true;try{const result=await api('/api/schedule',{start,end,rule:$('rule').value});renderResult(result,start,end);message('排程完成。請檢查逾期與未排入的訂單。');}catch(e){$('results').hidden=true;message(e.message,true);}finally{$('run').disabled=false;}};
['start','end','rule'].forEach(id=>$(id).addEventListener('change',()=>{$('results').hidden=true;}));
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
(async()=>{try{data=await api('/api/data');const now=new Date();now.setHours(8,0,0,0);const local=d=>new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);$('start').value=local(now);now.setDate(now.getDate()+5);$('end').value=local(now);renderEditor();}catch(e){message(e.message,true);}})();
