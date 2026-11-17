import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Button, Callout, FormGroup, InputGroup, TextArea} from '@blueprintjs/core';
import '@blueprintjs/core/lib/css/blueprint.css';

const h = React.createElement;
const defaultUrl = 'https://api.deepseek.com';
const system = '你是 BNBU 校园空间研究助手。仅根据用户提供的问题和当前视图上下文作答。校园模型、GIS、照片与遥感数据并非实地测绘，建筑和 DSM 未配准，不能据此断言真实通行、玻璃面积或鸟撞风险。没有证据时明确说明不确定，不要声称自己看到了未提供的数据。';
function App() {
 const [config, setConfig] = useState({url:defaultUrl, model:'deepseek-flash', key:''});
 const [settings, setSettings] = useState(false), [input,setInput] = useState(''), [messages,setMessages] = useState([]), [busy,setBusy] = useState(false), [error,setError] = useState('');
 const set = field => e => setConfig({...config,[field]:e.target.value});
 async function send(e) {
  e.preventDefault(); const content=input.trim(); if (!content || busy) return;
  if (!config.key.trim()) {setSettings(true);setError('请先配置 API Key。');return;}
  let endpoint;
  try { const url=new URL(config.url.trim()); if (!['https:','http:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw Error(); endpoint=url.toString().replace(/\/$/,'')+'/chat/completions'; }
  catch {setError('请输入有效的 HTTP(S) API 基础地址，不含查询参数。');return;}
  const selected=document.getElementById('selection')?.innerText || '未选择对象';
  const scene=document.getElementById('choose-dsm')?.classList.contains('selected') ? '遥感山体参考' : '校园三维模型';
  const context=`当前场景：${scene}。当前结构信息：${selected.slice(0,1500)}`;
  const next=[...messages,{role:'user',content}]; setMessages(next);setInput('');setError('');setBusy(true);
  try {
   const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${config.key.trim()}`},body:JSON.stringify({model:config.model.trim(),messages:[{role:'system',content:system+'\n'+context},...next],stream:false})});
   const body=await response.json().catch(()=>({}));
   if (!response.ok) throw new Error(body.error?.message || `HTTP ${response.status}`);
   const answer=body.choices?.[0]?.message?.content;
   if (typeof answer !== 'string' || !answer.trim()) throw new Error('接口没有返回有效的文本回复。');
   setMessages([...next,{role:'assistant',content:answer}]);
  } catch(err) {setMessages(messages);setInput(content);setError(`请求失败：${err.message}。请检查配置、网络和服务商的浏览器跨域支持。`);}
  finally {setBusy(false);}
 }
 return <div className="aip bp6-dark"><div className="aip-header"><div><span className="aip-kicker">BNBU · INTELLIGENCE</span><h2>空间研究助手</h2><span className="aip-sub">连接模型与研究问题</span></div><Button icon="cog" minimal aria-label="API 设置" onClick={()=>setSettings(!settings)}/></div>
 {settings && <div className="aip-settings"><div className="settings-title">模型连接 <span>OpenAI 兼容 API</span></div><FormGroup label="API 基础地址" labelFor="api-url"><InputGroup id="api-url" value={config.url} onChange={set('url')} /></FormGroup><FormGroup label="模型 ID" labelFor="api-model"><InputGroup id="api-model" value={config.model} onChange={set('model')} /></FormGroup><FormGroup label="API Key" labelFor="api-key"><InputGroup id="api-key" type="password" autoComplete="off" value={config.key} onChange={set('key')} placeholder="输入 API Key" /></FormGroup><p>密钥仅保留在当前页面内，关闭或刷新后需重新输入。请求直接发送到所填服务地址；服务商需允许浏览器跨域访问。</p><Button small intent="primary" onClick={()=>setSettings(false)}>完成</Button></div>}
 <div className="aip-messages" aria-live="polite">{messages.length===0 ? <div className="aip-empty"><div className="aip-spark">✳</div><div className="aip-kicker">CAMPUS INTELLIGENCE</div><h3>从空间开始提问</h3><p>探索校园模型、结构关系与已有研究资料。选择三维对象后，其当前信息会随问题一起发送。</p><button type="button" onClick={()=>setInput('这个模型能帮助我研究哪些鸟撞玻璃问题？')}>这个模型能帮助我研究哪些鸟撞玻璃问题？ <span>↗</span></button><button type="button" onClick={()=>setInput('解释当前模型的证据限制。')}>解释当前模型的证据限制 <span>↗</span></button></div> : messages.map((m,i)=><div className={'aip-message '+m.role} key={i}><div className="message-role">{m.role==='user'?'YOU':'AIP ASSISTANT'}</div><div className="message-content">{m.content}</div></div>)}{busy && <p className="aip-thinking">正在生成回答…</p>}</div>
 <div className="aip-compose">{error && <Callout intent="danger" role="alert">{error}</Callout>}<form onSubmit={send}><TextArea fill growVertically value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();e.currentTarget.form.requestSubmit();}}} placeholder="针对校园模型提问…" aria-label="输入消息"/><div className="compose-actions"><span>{config.model || '未设置模型'} · {config.key ? '已配置密钥' : '未配置密钥'}</span><Button type="submit" intent="primary" disabled={busy||!input.trim()} text="发送" /></div></form><div className="aip-note">回答可能有误；请结合证据与模型限制核实。</div></div></div>;
}
createRoot(document.getElementById('chat-root')).render(h(App));
const chat=document.getElementById('show-chat'), data=document.getElementById('show-data'), root=document.getElementById('chat-root'), pane=document.querySelector('.right-pane');
function switchPanel(showChat){root.hidden=!showChat;pane.hidden=showChat;chat.setAttribute('aria-selected',String(showChat));data.setAttribute('aria-selected',String(!showChat));if(!showChat) window.dispatchEvent(new Event('resize'));}
chat.addEventListener('click',()=>switchPanel(true));data.addEventListener('click',()=>switchPanel(false));
