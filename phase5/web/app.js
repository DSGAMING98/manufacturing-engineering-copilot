'use strict';
const specs = {
  design: { label:'Design Engineering', subtitle:'Worst-case clearance and interference between a hole and shaft.', icon:'◇',
    scope:'Only 1D worst-case hole/shaft fit. Not a tolerance-stack analysis or official fit designation.',
    fields:[['hole_min','Hole minimum (mm)','20.00'],['hole_max','Hole maximum (mm)','20.04'],['shaft_min','Shaft minimum (mm)','19.97'],['shaft_max','Shaft maximum (mm)','20.01'],['unit','Unit','mm']]},
  process: {label:'Process Planning', subtitle:'Estimate ideal spindle speed, feed rate and single-pass cutting time.', icon:'⚙',
    scope:'Idealized turning time only. Tool path, machine capability, safety and machining conditions require expert review.',
    fields:[['diameter_mm','Workpiece diameter (mm)','20'],['cutting_speed_m_per_min','Cutting speed (m/min)','100'],['feed_mm_per_rev','Feed (mm/revolution)','0.2'],['length_mm','Cut length (mm)','80']]},
  production: {label:'Production Engineering', subtitle:'Calculate availability, performance, quality and overall equipment effectiveness.', icon:'▤',
    scope:'Historical OEE based on provided figures. Inconsistent cycle-time reports are rejected.',
    fields:[['planned_min','Planned time (min)','480'],['run_min','Operating time (min)','420'],['ideal_cycle_min_per_part','Ideal cycle (min/part)','1'],['total_parts','Total parts','350'],['good_parts','Good parts','335']]},
  quality: {label:'Quality Assurance', subtitle:'Deterministic dimensional inspection using inclusive tolerance limits.', icon:'✓',
    scope:'PASS/FAIL means dimensional conformity only, not authorization to release parts or batches.',
    fields:[['nominal','Nominal size','20.00'],['measured','Measured size','20.03'],['tolerance','Symmetric tolerance (±)','0.05'],['unit','Unit (mm or in)','mm']]},
  maintenance: {label:'Maintenance Analytics', subtitle:'Retrospective reliability and observed availability metrics.', icon:'◷',
    scope:'Observed MTBF/MTTR are historical indicators, NOT remaining-useful-life predictions.',
    fields:[['operating_hours','Operating hours','800'],['repair_hours','Repair hours','20'],['failures','Recorded failures','4']]},
  documentation: {label:'Technical Documentation', subtitle:'Build a review-required inspection record draft from provided, traceable data.', icon:'▣',
    scope:'Generates DRAFT_NOT_APPROVED records only. No automatic signature, approval or compliance claim.',
    fields:[['record_id','Record ID','IR-001'],['feature_id','Feature ID','SHAFT-1'],['drawing_id','Drawing ID','DR-001'],['revision','Drawing revision','A'],['nominal','Nominal size','20'],['measured','Measured size','20.03'],['tolerance','Symmetric tolerance (±)','0.05'],['unit','Unit','mm'],['equipment_id','Gauge/equipment ID','GAUGE-7'],['timestamp','ISO-8601 timestamp with offset','2026-11-13T09:30:00+05:30'],['operator_id','Operator ID (optional)','']]},
  knowledge: {label:'Document Evidence', subtitle:'Search locally registered procedures; only exact, line-numbered excerpts are returned.', icon:'⌕',
    scope:'The hosted demo searches FICTIONAL example documents only. Local mode can use permission-cleared, human-reviewed files.',
    fields:[['question','Ask about a registered document','What identifiers belong in an inspection record for traceability?']]}
};
let active = 'design';
const $ = id => document.getElementById(id);
const nav = $('nav'), form = $('tool-form');
function node(tag, className, text) {
  const e = document.createElement(tag); if(className) e.className=className;
  if(text!==undefined) e.textContent=text; return e;
}
for (const [key, spec] of Object.entries(specs)) {
  const btn=node('button','nav-item'); btn.type='button'; btn.dataset.domain=key;
  const i=node('span','nav-icon',spec.icon), txt=node('span','nav-label',spec.label);
  btn.append(i,txt); btn.addEventListener('click',()=>activate(key)); nav.append(btn);
}
function activate(key) {
  active=key; const spec=specs[key];
  for(const btn of nav.children) {btn.classList.toggle('selected',btn.dataset.domain===key);btn.setAttribute('aria-current',btn.dataset.domain===key?'page':'false');}
  $('crumb-domain').textContent=key.toUpperCase();$('page-title').textContent=spec.label;
  $('page-subtitle').textContent=spec.subtitle;$('scope-text').textContent=spec.scope;
  $('form-title').textContent=key==='knowledge'?'DOCUMENT QUERY':'INPUT PARAMETERS';
  $('field-count').textContent=String(spec.fields.length).padStart(2,'0')+' FIELDS';
  $('fields').replaceChildren();
  for(const [id, label, value] of spec.fields) {
    const wrap=node('div','field'); const l=node('label','',label); l.htmlFor='field-'+id;
    const input=node(key==='knowledge'?'textarea':'input'); input.id='field-'+id;input.name=id;
    input.value=value;input.placeholder=label;input.autocomplete='off';
    if(key==='knowledge') input.rows=4; else input.type='text';
    wrap.append(l,input); $('fields').append(wrap);
  }
  $('run').querySelector('span').textContent=key==='knowledge'?'SEARCH EVIDENCE':'RUN CHECK';
  $('result').hidden=true;$('empty').hidden=false;$('output-mode').textContent='AWAITING INPUT';
}
form.addEventListener('submit',async e=>{
  e.preventDefault(); const key=active; const spec=specs[key]; const fields={};
  for(const [id] of spec.fields) {
    const value=$('field-'+id).value.trim(); if(value!=='') fields[id]=value;
  }
  const payload=key==='knowledge'?{domain:'knowledge',question:fields.question||''}:{domain:key,fields};
  $('run').disabled=true;$('output-mode').textContent='CALCULATING';
  try {
    const res=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const output=await res.json();
    $('empty').hidden=true;$('result').hidden=false;
    const status=output.data?.decision||output.data?.dimensional_check||output.data?.classification||output.status||'UNKNOWN';
    $('result-status').textContent=status;
    $('result-status').className='result-status '+(status==='PASS'||status==='CLEARANCE'?'good':status==='FAIL'||status==='INSUFFICIENT_DATA'||status==='NO_VERIFIED_SOURCE'?'warn':'neutral');
    $('result-text').textContent=output.report||'No report returned.';
    $('output-mode').textContent=output.mode||'RESULT';
    $('result-evidence').textContent=(output.citations&&output.citations.length)?'Citations: '+output.citations.join(', '):'Source: local calculation or refused evidence';
  } catch(err) {
    $('empty').hidden=true;$('result').hidden=false;$('result-status').textContent='ERROR';
    $('result-status').className='result-status warn';$('result-text').textContent=String(err);
    $('output-mode').textContent='NETWORK ERROR';$('result-evidence').textContent='';
  } finally { $('run').disabled=false; }
});
activate('design');
