import { useState } from 'react';

export default function KeywordTagInput({ value, onChange, placeholder, tone = 'include' }) {
  const [draft, setDraft] = useState('');

  function add(items) {
    const additions = items.map((item) => item.trim()).filter(Boolean);
    if (!additions.length) return;
    onChange([...new Set([...value, ...additions])]);
  }

  function updateDraft(event) {
    const text = event.target.value;
    if (!text.includes(',')) {
      setDraft(text);
      return;
    }
    const parts = text.split(',');
    add(parts.slice(0, -1));
    setDraft(parts.at(-1));
  }

  function commit() {
    if (!draft.trim()) return;
    add([draft]);
    setDraft('');
  }

  function keyDown(event) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      commit();
    } else if (event.key === 'Backspace' && !draft && value.length) {
      onChange(value.slice(0, -1));
    }
  }

  return <div className={`keyword-tag-input ${tone}`} onClick={(event) => event.currentTarget.querySelector('input')?.focus()}>
    {value.map((item) => <button key={item} type="button" className="keyword-tag" onClick={(event) => { event.stopPropagation(); onChange(value.filter((word) => word !== item)); }} title="Quitar palabra"><span>{item}</span><b aria-hidden="true">×</b></button>)}
    <input value={draft} onChange={updateDraft} onKeyDown={keyDown} onBlur={commit} placeholder={value.length ? 'Agregar otra…' : placeholder} />
  </div>;
}
