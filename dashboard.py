"""RingGuard AI — redesigned risk-operations frontend.

Run with: streamlit run dashboard.py
The detection, Gemini, and audit modules are reused unchanged.
"""
from __future__ import annotations
import json, sys, time
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from detector import run_detection
from agent import analyze_all_rings
from audit import log_detection, get_log

DATA = HERE / "data"
st.set_page_config(page_title="RingGuard AI · Risk Operations", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

st.markdown(r'''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#080b12;--panel:#0f141e;--line:#202938;--text:#f4f7fb;--muted:#8f9bad;--soft:#c3ccd8;--red:#ff5d62;--red2:#ff8b7e;--green:#42d6a1;--blue:#6ea8ff;--amber:#f3b96b}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}.stApp{background:radial-gradient(900px 420px at 72% -10%,rgba(71,100,164,.18),transparent 60%),radial-gradient(700px 350px at -10% 50%,rgba(255,93,98,.08),transparent 65%),var(--bg);color:var(--text)}#MainMenu,footer{visibility:hidden}.block-container{max-width:1520px!important;padding:1.1rem 2rem 4rem!important}
[data-testid="stSidebar"]{background:rgba(9,12,18,.97)!important;border-right:1px solid var(--line)!important}[data-testid="stSidebar"] h3{font-size:.68rem!important;text-transform:uppercase!important;letter-spacing:.13em!important;color:var(--muted)!important;margin:1rem 0 .45rem!important}[data-testid="stSidebar"] hr{border-color:var(--line)!important}
div[data-baseweb="select"]>div,div[data-baseweb="input"]>div{background:#0d131d!important;border:1px solid var(--line)!important;color:var(--text)!important;border-radius:10px!important}.stButton>button{background:#121925!important;color:var(--text)!important;border:1px solid #273243!important;border-radius:10px!important;font-weight:600!important;min-height:2.45rem!important}.stButton>button:hover{background:#182130!important;border-color:#3a485d!important}
[data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(180deg,rgba(18,25,37,.96),rgba(13,18,27,.96))!important;border:1px solid var(--line)!important;border-radius:16px!important;box-shadow:0 12px 38px rgba(0,0,0,.22)!important;padding:.45rem .65rem!important}[data-testid="metric-container"]{background:#0d131d!important;border:1px solid #1e2836!important;border-radius:14px!important;padding:1rem 1.05rem!important}[data-testid="stMetricLabel"]{color:var(--muted)!important;font-size:.7rem!important;text-transform:uppercase;letter-spacing:.1em!important}[data-testid="stMetricValue"]{color:var(--text)!important;font-family:'Space Grotesk',sans-serif!important;font-size:2rem!important;font-weight:700!important}
[data-testid="stTabs"]>div:first-child{border-bottom:1px solid var(--line)!important}[data-testid="stTabs"] button{color:var(--muted)!important;font-weight:600!important;padding:.72rem 1.15rem!important;font-size:.86rem!important}[data-testid="stTabs"] button[aria-selected="true"]{color:var(--text)!important;border-bottom:2px solid var(--red)!important;background:rgba(255,93,98,.05)!important}
[data-testid="stDataFrame"]{border:1px solid var(--line)!important;border-radius:12px!important;overflow:hidden!important}
.brand{display:flex;align-items:center;gap:12px;margin:.25rem 0 1rem}.mark{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(145deg,#1a2434,#0d121b);border:1px solid #2a3648;color:var(--red);font-size:1.2rem}.brandname{font:700 1.15rem 'Space Grotesk',sans-serif}.brandsub{color:var(--muted);font-size:.67rem;letter-spacing:.08em;text-transform:uppercase;margin-top:2px}
.hero{position:relative;overflow:hidden;border:1px solid #263143;border-radius:20px;padding:1.45rem 1.6rem 1.35rem;margin-bottom:1rem;background:radial-gradient(550px 220px at 88% -20%,rgba(110,168,255,.14),transparent 65%),linear-gradient(145deg,#111926,#0d121b 55%,#111620)}.kicker{color:var(--green);font-size:.68rem;letter-spacing:.15em;text-transform:uppercase;font-weight:700}.hero h1{font:700 2.45rem/1.05 'Space Grotesk',sans-serif;letter-spacing:-.04em;margin:.35rem 0 .45rem}.hero p{color:var(--soft);margin:0;max-width:780px;font-size:.95rem;line-height:1.55}.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:1rem}.chip{border:1px solid #273344;background:#0b1119;padding:5px 9px;border-radius:8px;font:500 .69rem 'DM Mono',monospace;color:var(--soft)}.chip b{color:var(--text)}
.eyebrow{color:var(--muted);font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;font-weight:700;margin-bottom:.28rem}.title{font:700 1.15rem 'Space Grotesk',sans-serif;margin:0 0 .8rem}.title span{color:var(--muted);font:500 .78rem 'DM Sans',sans-serif;margin-left:.45rem}
.priority{background:linear-gradient(145deg,rgba(92,20,27,.18),#111720 55%);border:1px solid rgba(255,93,98,.28);border-radius:16px;padding:1rem 1.05rem}.badge{color:var(--red2);font-size:.65rem;text-transform:uppercase;letter-spacing:.12em;font-weight:700}.riskname{font:700 1.2rem 'Space Grotesk',sans-serif;margin:.35rem 0 .1rem}.meta{color:var(--muted);font-size:.77rem}.score{font:700 2.2rem 'Space Grotesk',sans-serif;color:var(--red2);line-height:1}.progress{height:7px;border-radius:99px;background:#252d39;margin:.65rem 0 .8rem;overflow:hidden}.progress>div{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--red),var(--red2))}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.stat{background:#0b1118;border:1px solid #202936;border-radius:10px;padding:.62rem}.stat .n{font:600 .98rem 'DM Mono',monospace}.stat .l{font-size:.62rem;color:var(--muted);margin-top:2px;text-transform:uppercase}.callout{border:1px solid #253042;background:#0b1118;border-radius:12px;padding:.82rem .9rem;color:var(--soft);font-size:.77rem;line-height:1.55}.callout b{color:var(--text)}
.signal{display:flex;align-items:center;justify-content:space-between;padding:.7rem 0;border-bottom:1px solid #1d2633}.signal:last-child{border-bottom:0}.signal .left{display:flex;align-items:center;gap:10px}.signal .icon{width:26px;height:26px;border-radius:8px;background:#121b28;border:1px solid #263143;display:grid;place-items:center;color:var(--red2)}.signal .name{font-size:.77rem;font-weight:600}.signal .sub{color:var(--muted);font-size:.64rem}.weight{font:500 .75rem 'DM Mono',monospace;color:var(--red2)}
.ring{border:1px solid #202a37;border-radius:13px;padding:.85rem .95rem;background:#0c121a}.ring.active{border-color:rgba(255,93,98,.3);box-shadow:inset 3px 0 0 var(--red)}.ringtop{display:flex;justify-content:space-between}.ringid{font:600 .78rem 'DM Mono',monospace}.ringscore{font:600 .72rem 'DM Mono',monospace;color:var(--red2)}.ringdesc{color:var(--muted);font-size:.72rem;line-height:1.45;margin-top:.35rem}.audit{display:grid;grid-template-columns:110px 160px 90px 90px 1fr;gap:12px;align-items:center;border:1px solid #1f2835;background:#0c1219;padding:.65rem .8rem;border-radius:10px;margin-bottom:.45rem;font-size:.71rem}.audit .id{font-family:'DM Mono',monospace;color:var(--red2)}.muted{color:var(--muted)}.ok{color:var(--green)}.warn{color:var(--amber)}
@media(max-width:900px){.block-container{padding-left:1rem!important;padding-right:1rem!important}.hero h1{font-size:1.95rem}.audit{grid-template-columns:1fr 1fr}}
</style>''', unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def data(name):
    with open(DATA/name,encoding='utf-8') as f:return pd.DataFrame(json.load(f))
@st.cache_data(show_spinner=False,ttl=20)
def detection():
    _,rings,metrics=run_detection();return analyze_all_rings(rings),metrics
@st.cache_data(show_spinner=False,ttl=10)
def audit():return get_log()

merchants=data('merchants.json'); txns=data('transactions.json'); returns=data('returns.json'); txns['timestamp']=pd.to_datetime(txns['timestamp']); txns['date']=txns['timestamp'].dt.date
rings,metrics=detection(); logs=audit()

with st.sidebar:
    st.markdown('<div class="brand"><div class="mark">◈</div><div><div class="brandname">RingGuard <span style="color:#ff8b7e">AI</span></div><div class="brandsub">Risk Intelligence · Track 02</div></div></div>',unsafe_allow_html=True)
    damage=sum(r['total_damage_inr'] for r in rings)
    st.markdown(f'<div class="callout"><span style="color:var(--green)">● LIVE</span><br><span class="muted">{len(rings)} active rings · ₹{damage:,} surfaced</span></div>',unsafe_allow_html=True)
    st.markdown('### Risk lens'); threshold=st.slider('Minimum confidence',0,100,50,5)
    cats=['All']+sorted(merchants['category'].unique().tolist()); cat=st.selectbox('Merchant category',cats)
    st.markdown('### Investigate'); filtered=merchants if cat=='All' else merchants[merchants.category==cat]; opts=['— none —']+filtered.merchant_id.tolist(); selected=st.selectbox('Jump to merchant',opts)
    if st.button('↻ Re-run detection',use_container_width=True): detection.clear(); st.rerun()
    st.divider(); st.markdown('<div style="font-size:.65rem;color:#596575;text-align:center">DEFENSE-ONLY · SYNTHETIC DATA · HUMAN REVIEW</div>',unsafe_allow_html=True)

active=[r for r in rings if r['confidence_score']>=threshold]; total=len(txns); fraud=int(txns['is_fraud'].sum()); rate=fraud/total if total else 0; exposure=sum(r['total_damage_inr'] for r in active)
st.markdown(f'<div class="hero"><div class="kicker">● Monitoring cross-merchant abuse patterns</div><h1>Risk operations, built around the ring.</h1><p>RingGuard connects return events across merchants, scores coordinated behavior, and gives investigators an AI-assisted explanation before human review.</p><div class="chips"><span class="chip">Merchants <b>{len(merchants)}</b></span><span class="chip">Transactions <b>{total:,}</b></span><span class="chip">Rings <b>{len(active)}</b></span><span class="chip">Loss surfaced <b>₹{exposure:,}</b></span><span class="chip">Audit runs <b>{len(logs)}</b></span></div></div>',unsafe_allow_html=True)

over,graph,explorer,ledger=st.tabs(['Overview','Ring network','Merchant explorer','Audit ledger'])
COLORS={'RING_1':'#ff5d62','RING_2':'#42d6a1','RING_3':'#6ea8ff','RING_4':'#f3b96b','RING_5':'#b18cff'}

with over:
    a,b,c,d=st.columns(4,gap='medium'); a.metric('Transactions',f'{total:,}'); b.metric('Active rings',len(active),f'≥ {threshold}% confidence'); c.metric('Fraud rate',f'{rate*100:.2f}%'); d.metric('Loss surfaced',f'₹{exposure:,}',f'{len(returns)} return events')
    st.markdown('<div style="height:.85rem"></div>',unsafe_allow_html=True)
    l,r=st.columns([1.7,1],gap='medium')
    with l:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">Primary signal</div><div class="title">Highest-confidence ring <span>lead investigation</span></div>',unsafe_allow_html=True)
            if active:
                q=active[0]; s=q['confidence_score']; v=q.get('llm_verdict','')
                st.markdown(f'<div class="priority"><div class="badge">● HIGH PRIORITY · {q["cluster_id"]}</div><div class="riskname">Coordinated cross-merchant abuse pattern</div><div class="meta">{q["member_count"]} members · {q["merchant_count"]} merchants · ₹{q["total_damage_inr"]:,} surfaced</div><div style="display:flex;align-items:end;justify-content:space-between;margin-top:.9rem"><div style="flex:1"><div class="meta">CONFIDENCE</div><div class="progress"><div style="width:{s}%"></div></div></div><div style="text-align:right;margin-left:15px"><div class="score">{s}</div><div class="meta">/ 100</div></div></div><div class="stats"><div class="stat"><div class="n">{q["member_count"]}</div><div class="l">Actors</div></div><div class="stat"><div class="n">{q["merchant_count"]}</div><div class="l">Merchants</div></div><div class="stat"><div class="n">{q["signals"]["unique_devices"]}</div><div class="l">Devices</div></div></div></div><div class="callout" style="margin-top:.7rem"><b>AI summary</b><br>{v}</div>',unsafe_allow_html=True)
            else: st.info('No rings meet the current confidence threshold.')
    with r:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">Why it was flagged</div><div class="title">Evidence stack</div>',unsafe_allow_html=True)
            sigs=[('⌁','Device match','Shared device fingerprint','+3'),('◎','BIN match','Same issuing bank BIN','+2'),('⊙','PIN cluster','PINs within ±2','+2'),('◷','Timing','Returns within 48 hours','+1')]
            for icon,name,sub,w in sigs: st.markdown(f'<div class="signal"><div class="left"><div class="icon">{icon}</div><div><div class="name">{name}</div><div class="sub">{sub}</div></div></div><div class="weight">{w}</div></div>',unsafe_allow_html=True)
            st.markdown('<div class="callout" style="margin-top:.65rem"><b>Detection rule</b><br>Edge weight ≥ 3 · ring size ≥ 3 · merchants ≥ 2.</div>',unsafe_allow_html=True)
    st.markdown('<div style="height:.85rem"></div>',unsafe_allow_html=True)
    l,r=st.columns([1.55,1],gap='medium')
    with l:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">30-day volume</div><div class="title">Transactions vs flagged activity</div>',unsafe_allow_html=True)
            daily=txns.groupby(['date','is_fraud']).size().unstack(fill_value=0); dates=sorted(txns.date.unique()); fig=go.Figure(); fig.add_trace(go.Scatter(x=dates,y=daily.get(False,pd.Series(dtype=int)).reindex(dates,fill_value=0),name='Legitimate',mode='lines',line=dict(color='#42d6a1',width=2),fill='tozeroy',fillcolor='rgba(66,214,161,.08)')); fig.add_trace(go.Scatter(x=dates,y=daily.get(True,pd.Series(dtype=int)).reindex(dates,fill_value=0),name='Fraud',mode='lines+markers',line=dict(color='#ff5d62',width=2),marker=dict(size=4))); fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=235,margin=dict(l=0,r=0,t=10,b=0),legend=dict(orientation='h',y=1.12,bgcolor='rgba(0,0,0,0)',font=dict(color='#9aa5b4')),xaxis=dict(showgrid=False,color='#697689'),yaxis=dict(gridcolor='#1b2430',color='#697689')); st.plotly_chart(fig,use_container_width=True)
    with r:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">Exposure mix</div><div class="title">Ring damage split</div>',unsafe_allow_html=True)
            if active:
                fig=go.Figure(go.Pie(labels=[x['cluster_id'] for x in active],values=[x['total_damage_inr'] for x in active],hole=.68,marker=dict(colors=[COLORS.get(x['cluster_id'],'#ff5d62') for x in active],line=dict(color='#0f141e',width=2)),textinfo='label+percent')); fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',height=235,margin=dict(l=0,r=0,t=5,b=0),showlegend=False,font=dict(color='#eef2f7')); st.plotly_chart(fig,use_container_width=True)
    st.markdown('<div style="height:.85rem"></div>',unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f'<div class="eyebrow">{len(active)} cases in focus</div><div class="title">Active rings <span>sorted by confidence</span></div>',unsafe_allow_html=True)
        cols=st.columns(min(3,max(1,len(active))))
        for i,q in enumerate(active):
            with cols[i%len(cols)]:
                color=COLORS.get(q['cluster_id'],'#ff5d62'); text=q.get('llm_verdict',''); st.markdown(f'<div class="ring {"active" if i==0 else ""}" style="border-left:3px solid {color}"><div class="ringtop"><div class="ringid">{q["cluster_id"]}</div><div class="ringscore">{q["confidence_score"]}/100</div></div><div class="ringdesc">{q["member_count"]} members · {q["merchant_count"]} merchants · ₹{q["total_damage_inr"]:,}</div><div class="progress" style="height:5px"><div style="width:{q["confidence_score"]}%;background:{color}"></div></div><div class="ringdesc">{text[:180]}{"…" if len(text)>180 else ""}</div></div>',unsafe_allow_html=True)

with graph:
    import networkx as nx
    st.markdown('<div class="eyebrow">Relationship map</div><div class="title">Fraud ring network <span>shared signals create the links</span></div>',unsafe_allow_html=True)
    show=st.toggle('Show legitimate comparison nodes',False); chosen=st.multiselect('Rings',[r['cluster_id'] for r in rings],default=[r['cluster_id'] for r in rings]); selected_rings=[r for r in rings if r['cluster_id'] in chosen]
    G=nx.Graph()
    for q in selected_rings:
        ms=q['members']
        for m in ms:G.add_node(m['txn_id'],ring=q['cluster_id'],merchant=m['merchant_id'],amount=m['amount'],device=m['device_fingerprint'][:8]+'…',bin=m['bank_bin'])
        for i in range(len(ms)):
            for j in range(i+1,len(ms)):
                w=(3 if ms[i]['device_fingerprint']==ms[j]['device_fingerprint'] else 0)+(2 if ms[i]['bank_bin']==ms[j]['bank_bin'] else 0)
                try:w+=2 if abs(int(ms[i]['pin'])-int(ms[j]['pin']))<=2 else 0
                except (ValueError,TypeError):pass
                if w>=3:G.add_edge(ms[i]['txn_id'],ms[j]['txn_id'])
    if show:
        for _,m in returns[~returns.is_fraud].head(12).iterrows():G.add_node(m.txn_id,ring='legit',merchant=m.merchant_id,amount=m.amount,device='legit',bin=m.bank_bin)
    if G.nodes:
        pos=nx.spring_layout(G,seed=42,k=1.8); fig=go.Figure(); ex=[];ey=[]
        for u,v in G.edges:x0,y0=pos[u];x1,y1=pos[v];ex += [x0,x1,None];ey += [y0,y1,None]
        if ex:fig.add_trace(go.Scatter(x=ex,y=ey,mode='lines',line=dict(color='rgba(120,140,165,.28)',width=1.8),hoverinfo='none',showlegend=False))
        ns=list(G.nodes()); fig.add_trace(go.Scatter(x=[pos[n][0] for n in ns],y=[pos[n][1] for n in ns],mode='markers',marker=dict(size=[19 if G.nodes[n]['ring']!='legit' else 9 for n in ns],color=[COLORS.get(G.nodes[n]['ring'],'#596575') for n in ns],line=dict(color='#e9eef5',width=1.4)),text=[f"<b>{n}</b><br>Ring: {G.nodes[n]['ring']}<br>Merchant: {G.nodes[n]['merchant']}<br>Amount: ₹{G.nodes[n]['amount']:,}<br>Device: {G.nodes[n]['device']}<br>BIN: {G.nodes[n]['bin']}" for n in ns],hovertemplate='%{text}<extra></extra>',showlegend=False)); fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=560,margin=dict(l=0,r=0,t=10,b=0),xaxis=dict(showgrid=False,showticklabels=False),yaxis=dict(showgrid=False,showticklabels=False));
        with st.container(border=True):st.plotly_chart(fig,use_container_width=True)
    else:st.info('Select at least one ring.')

with explorer:
    st.markdown('<div class="eyebrow">Investigate an entity</div><div class="title">Merchant explorer <span>risk context follows the selected merchant</span></div>',unsafe_allow_html=True)
    s=st.text_input('Search',placeholder='Merchant name or ID…'); summary=txns.groupby('merchant_id').agg(total_txns=('txn_id','count'),revenue=('amount','sum'),fraud=('is_fraud','sum')).reset_index();summary['risk_rate']=(summary.fraud/summary.total_txns*100).round(2);table=merchants.merge(summary,on='merchant_id',how='left').fillna(0);ringids=set(m for r in rings for m in r['merchants_hit']);table['in_ring']=table.merchant_id.isin(ringids)
    if s:table=table[table.merchant_id.str.contains(s,case=False)|table.name.str.contains(s,case=False)]
    if cat!='All':table=table[table.category==cat]
    table=table.sort_values(['in_ring','risk_rate'],ascending=[False,False]); l,r=st.columns([1.25,1.75],gap='medium')
    with l:
        with st.container(border=True):st.markdown(f'<div class="eyebrow">{len(table)} merchants</div><div class="title">Risk-ranked directory</div>',unsafe_allow_html=True); d=table[['merchant_id','name','category','total_txns','fraud','risk_rate','in_ring']].copy();d.columns=['ID','Merchant','Category','Txns','Fraud','Risk %','Ring'];d['Ring']=d.Ring.map({True:'● Yes',False:'—'});st.dataframe(d,use_container_width=True,height=430,hide_index=True)
    with r:
        if selected=='— none —':
            with st.container(border=True):st.markdown('<div style="padding:5rem 2rem;text-align:center"><div class="eyebrow">Start here</div><div style="font:600 1rem Space Grotesk;color:#dce3ed">Select a merchant from the sidebar.</div><div class="muted" style="font-size:.74rem">See transaction pressure, fraud exposure, and ring involvement.</div></div>',unsafe_allow_html=True)
        else:
            row=merchants[merchants.merchant_id==selected]
            if row.empty:st.warning('Merchant not found.')
            else:
                info=row.iloc[0];mt=txns[txns.merchant_id==selected].sort_values('timestamp',ascending=False);mf=int(mt.is_fraud.sum());rev=int(mt.amount.sum());risk=mf/len(mt)*100 if len(mt) else 0;inring=selected in ringids
                with st.container(border=True):
                    st.markdown(f'<div class="eyebrow">{info.category.title()}</div><div class="title" style="font-size:1.45rem">{info.name}</div><div class="meta">{selected} · <span style="color:{"var(--red2)" if inring else "var(--green)"}">● {"Active ring exposure" if inring else "Clean"}</span></div>',unsafe_allow_html=True);a,b,c,d=st.columns(4);a.metric('Transactions',len(mt));b.metric('Revenue',f'₹{rev:,}');c.metric('Fraud',mf,f'{risk:.1f}% risk');d.metric('Ring','EXPOSED' if inring else 'CLEAN');
                    if inring:
                        for q in rings:
                            if selected in q['merchants_hit']:st.markdown(f'<div class="priority" style="margin-top:.8rem"><div class="badge">{q["cluster_id"]} · {q["confidence_score"]}/100</div><div class="meta" style="margin:.4rem 0">{q["member_count"]} members · ₹{q["total_damage_inr"]:,} impact</div><div class="callout">{q.get("llm_verdict","")}</div></div>',unsafe_allow_html=True)
                    md=mt.groupby(['date','is_fraud'])['amount'].sum().reset_index();dates=sorted(mt.date.unique());leg=md[~md.is_fraud].set_index('date').amount;fra=md[md.is_fraud].set_index('date').amount;fig=go.Figure();fig.add_trace(go.Bar(x=dates,y=leg.reindex(dates,fill_value=0),name='Legitimate',marker_color='rgba(66,214,161,.65)'));fig.add_trace(go.Bar(x=dates,y=fra.reindex(dates,fill_value=0),name='Fraud',marker_color='rgba(255,93,98,.75)'));fig.update_layout(barmode='stack',paper_bgcolor='rgba(0,0,0,0)',height=185,margin=dict(l=0,r=0,t=0,b=0),legend=dict(orientation='h',y=1.08,bgcolor='rgba(0,0,0,0)'));st.plotly_chart(fig,use_container_width=True);st.dataframe(mt[['txn_id','customer_name','amount','timestamp','is_fraud','bank_bin']].head(30),use_container_width=True,height=240,hide_index=True)

with ledger:
    l,r=st.columns([2,1],gap='medium')
    with l:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">Operational controls</div><div class="title">Detection + audit sync</div>',unsafe_allow_html=True)
            if st.button('⚡ Run audit sync',use_container_width=True):
                with st.spinner('Running detection pipeline…'): _,rr,mm=run_detection();rr=analyze_all_rings(rr);entry=log_detection(rr,mm,source='manual_ui');audit.clear()
                st.success(f'{entry["run_id"]} complete · {len(rr)} rings logged')
            st.markdown('<div class="callout" style="margin-top:.7rem">Every run records ring summaries, precision/recall, false-positive cost, and the AI verdict.</div>',unsafe_allow_html=True)
    with r:
        with st.container(border=True):
            st.markdown('<div class="eyebrow">Detection health</div><div class="title">Model performance</div>',unsafe_allow_html=True);a,b,c=st.columns(3);a.metric('Precision',f"{metrics.get('precision',0)*100:.0f}%");b.metric('Recall',f"{metrics.get('recall',0)*100:.0f}%");c.metric('FP cost',f"₹{metrics.get('false_positive_cost_inr',0):,}")
    st.markdown('<div style="height:.8rem"></div>',unsafe_allow_html=True);q=st.text_input('Search audit',placeholder='Run ID, source, ring count…');fresh=audit()
    if fresh:
        rows=[{'Run ID':e['run_id'],'Timestamp':e['timestamp'][:19].replace('T',' '),'Source':e.get('source','auto'),'Rings':e['rings_detected'],'Precision':f"{e['metrics'].get('precision',0)*100:.0f}%",'Recall':f"{e['metrics'].get('recall',0)*100:.0f}%",'FP Cost ₹':e['metrics'].get('false_positive_cost_inr',0)} for e in fresh];adf=pd.DataFrame(rows)
        if q:adf=adf[adf.astype(str).apply(lambda x:x.str.contains(q,case=False,regex=False)).any(axis=1)]
        with st.container(border=True):st.markdown(f'<div class="eyebrow">{len(adf)} visible entries</div><div class="title">Detection history</div>',unsafe_allow_html=True);st.dataframe(adf,use_container_width=True,height=300,hide_index=True)
        for e in reversed(fresh[-12:]):
            m=e['metrics'];p=m.get('precision',0);st.markdown(f'<div class="audit"><span class="id">{e["run_id"]}</span><span class="muted">{e["timestamp"][:19].replace("T"," ")}</span><span class="{"ok" if p>=.9 else "warn"}">{p*100:.0f}% precision</span><span>Rings <b>{e["rings_detected"]}</b></span><span class="muted">{", ".join(x["cluster_id"] for x in e.get("ring_summary",[])[:3])} · {e.get("source","auto")}</span></div>',unsafe_allow_html=True)
        with st.expander('Inspect latest raw JSON'):st.json(fresh[-1])
    else:st.info('No audit entries yet. Run an audit sync to create the first record.')
    st.markdown('<div class="callout" style="margin-top:.8rem"><b>Defense-only policy.</b> RingGuard surfaces coordinated fraud patterns for human review. It does not block transactions, automatically penalise customers, or expose raw PII. All data shown is synthetic.</div>',unsafe_allow_html=True)
