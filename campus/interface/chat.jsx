import React, {useEffect, useRef, useState, useSyncExternalStore} from 'react';
import {createRoot} from 'react-dom/client';
import {Button, Callout, Card, FormGroup, Icon, InputGroup, Tag, TextArea} from '@blueprintjs/core';
import '@blueprintjs/core/lib/css/blueprint.css';
import {apiContext, factText, getWorkspaceContext, pendingPaneAnswer, readFactSelection, refreshWorkspaceContext, revealWorkspaceEvidence, subscribeWorkspace} from './pane_evidence.js';

const h = React.createElement;
const defaultUrl = 'https://api.deepseek.com';
const system = '你是 BNBU 校园空间研究助手。仅根据用户提供的问题和当前视图上下文作答。校园模型、GIS、照片与遥感数据并非实地测绘，建筑和 DSM 未配准，不能据此断言真实通行、玻璃面积或鸟撞风险。没有证据时明确说明不确定，不要声称自己看到了未提供的数据。';
const paneSystem = '解释当前窗片时，从 facts 中挑选能回答问题的事实，包括缺失、冲突和待验证的条目。回复仅输出 JSON 对象 {"pane_id":"当前窗片ID","fact_ids":["允许的事实ID"]}。界面根据事实原文展示回答、单位、日期和来源。';
function App() {
 const [config, setConfig] = useState({url:defaultUrl, model:'deepseek-flash', key:''});
 const [settings, setSettings] = useState(false), [input,setInput] = useState(''), [messages,setMessages] = useState([]), [busy,setBusy] = useState(false), [error,setError] = useState('');
 const workspace = useSyncExternalStore(subscribeWorkspace,getWorkspaceContext);
 const requestRef = useRef(null);
 useEffect(()=>{
  requestRef.current?.abort();
  requestRef.current=null;
  setMessages([]);
  setBusy(false);
  setError('');
  setInput('');
 },[workspace]);
 const set = field => e => setConfig({...config,[field]:e.target.value});
 async function send(e) {
  e.preventDefault(); const content=input.trim(); if (!content || busy) return;
  const context=refreshWorkspaceContext();
  if (context!==workspace) return;
  const localAnswer=context.pane ? null : pendingPaneAnswer(content);
  if (localAnswer) {
   setMessages([...messages,{role:'user',content,local:true},{role:'assistant',content:localAnswer,local:true}]);
   setInput('');setError('');
   return;
  }
  if (!config.key.trim()) {setSettings(true);setError('请先配置 API Key。');return;}
  let endpoint;
  try {
   const url=new URL(config.url.trim());
   const local=['localhost','127.0.0.1','[::1]'].includes(url.hostname);
   if ((url.protocol!=='https:' && !(url.protocol==='http:' && local)) || url.username || url.password || url.search || url.hash) throw Error();
   endpoint=url.toString().replace(/\/$/,'')+'/chat/completions';
  } catch {setError('请输入有效的 HTTPS API 基础地址，或本机 HTTP 地址。');return;}
  const request=new AbortController();
  requestRef.current=request;
  const instructions=context.pane ? paneSystem : system;
  const contextMessage=instructions+'\n当前场景及结构化证据：'+JSON.stringify(apiContext(context));
  const next=[...messages,{role:'user',content}]; setMessages(next);setInput('');setError('');setBusy(true);
  try {
   const history=next.filter(message=>!message.local).map(message=>({role:message.role,content:message.wire??message.content}));
   const response=await fetch(endpoint,{method:'POST',signal:request.signal,headers:{'Content-Type':'application/json','Authorization':`Bearer ${config.key.trim()}`},body:JSON.stringify({model:config.model.trim(),messages:[{role:'system',content:contextMessage},...history],stream:false})});
   const body=await response.json().catch(()=>({}));
   if (!response.ok) throw new Error(body.error?.message || `HTTP ${response.status}`);
   const answer=body.choices?.[0]?.message?.content;
   if (typeof answer !== 'string' || !answer.trim()) throw new Error('接口没有返回有效的文本回复。');
   if (request.signal.aborted || refreshWorkspaceContext()!==context) return;
   const facts=context.pane ? readFactSelection(answer,context) : null;
   const guardedAnswer=facts ? null : pendingPaneAnswer(answer);
   const reply=facts ? {role:'assistant',facts,wire:JSON.stringify({pane_id:context.pane.pane_id,fact_ids:facts.map(fact=>fact.id)})}
    : {role:'assistant',content:guardedAnswer??answer,local:!!guardedAnswer};
   setMessages([...next,reply]);
  } catch(err) {
   if (!request.signal.aborted && refreshWorkspaceContext()===context) {
    setMessages(messages);setInput(content);
    setError(`请求失败：${err.message}。请检查接口回复、配置、网络和服务商的浏览器跨域支持。`);
   }
  } finally {
   if (requestRef.current===request) {requestRef.current=null;setBusy(false);}
  }
 }
 return <div className="aip"><div className="aip-header"><div><h3 className="bp6-heading">空间研究助手</h3><span className="bp6-text-muted">使用自然语言分析校园空间模型</span></div><Button icon="cog" minimal aria-label="API 设置" onClick={()=>setSettings(!settings)}/></div>
 {settings && <Card className="aip-settings" compact><h4 className="bp6-heading">模型连接</h4><p className="bp6-text-muted">OpenAI 兼容 API</p><FormGroup label="API 基础地址" labelFor="api-url"><InputGroup id="api-url" value={config.url} onChange={set('url')} /></FormGroup><FormGroup label="模型 ID" labelFor="api-model"><InputGroup id="api-model" value={config.model} onChange={set('model')} /></FormGroup><FormGroup label="API Key" labelFor="api-key"><InputGroup id="api-key" type="password" autoComplete="off" value={config.key} onChange={set('key')} placeholder="输入 API Key" /></FormGroup><p className="bp6-text-muted">密钥仅保留在当前页面内，关闭或刷新后需重新输入。请求直接发送到所填服务地址；服务商需允许浏览器跨域访问。</p><Button intent="primary" onClick={()=>setSettings(false)}>完成</Button></Card>}
 <div className="aip-messages" aria-live="polite">{workspace.pane && <p className="bp6-text-muted">当前窗片 {workspace.pane.pane_id}{workspace.status==='synthetic'?'（合成示例）':workspace.status==='stale'?'（证据包已过期）':''}</p>}{messages.length===0 ? <div className="aip-empty"><Icon icon="chat" size={24}/><h4 className="bp6-heading">从空间开始提问</h4><p className="bp6-text-muted">窗片查询与模型详情使用同一份证据。发送问题时，兼容 API 会收到当前场景、问题及可展示事实。</p><Button fill alignText="left" icon="search" text="这个模型能帮助我研究哪些鸟撞玻璃问题？" onClick={()=>setInput('这个模型能帮助我研究哪些鸟撞玻璃问题？')}/><Button fill alignText="left" icon="document" text="解释当前模型的证据限制" onClick={()=>setInput('解释当前模型的证据限制。')}/></div> : messages.map((m,i)=><div className={'aip-message '+m.role} key={i}><div className="message-role bp6-text-muted">{m.role==='user'?'你':'空间研究助手'}</div><Card compact className="message-content">{m.facts ? <ul>{m.facts.map(fact=><li key={fact.id}>{factText(fact)} <Button minimal small onClick={()=>revealWorkspaceEvidence(fact.id)} text="查看证据"/></li>)}</ul> : m.content}</Card></div>)}{busy && <p className="bp6-text-muted">正在生成回答…</p>}</div>
 <div className="aip-compose">{error && <Callout intent="danger" role="alert">{error}</Callout>}<form onSubmit={send}><TextArea fill growVertically value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();e.currentTarget.form.requestSubmit();}}} placeholder="针对校园模型提问…" aria-label="输入消息"/><div className="compose-actions"><Tag minimal icon="application">{config.model || '未设置模型'}</Tag><span className="bp6-text-muted">{config.key ? '已配置密钥' : '未配置密钥'}</span><Button type="submit" intent="primary" icon="send-message" disabled={busy||!input.trim()} text="发送" /></div></form><div className="bp6-text-muted aip-note">回答可能有误；请结合证据与模型限制核实。</div></div></div>;
}
createRoot(document.getElementById('chat-root')).render(h(App));
const chat=document.getElementById('show-chat'), data=document.getElementById('show-data'), root=document.getElementById('chat-root'), pane=document.querySelector('.right-pane');
function switchPanel(showChat){root.hidden=!showChat;pane.hidden=showChat;chat.setAttribute('aria-selected',String(showChat));data.setAttribute('aria-selected',String(!showChat));if(!showChat) window.dispatchEvent(new Event('resize'));}
chat.addEventListener('click',()=>switchPanel(true));data.addEventListener('click',()=>switchPanel(false));
for (const tab of [chat,data]) tab.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tab.click();}});
