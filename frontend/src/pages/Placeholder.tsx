export function Placeholder({ title, description, phase }: { title: string; description: string; phase: string }) {
  return <>
    <section className="page-heading"><div><p className="eyebrow">{phase}</p><h1>{title}</h1><p>{description}</p></div></section>
    <section className="panel placeholder">
      <span className="placeholder-mark" aria-hidden="true" />
      <h2>Foundation hazır</h2>
      <p>Bu modülün sözleşmesi ayrıldı; donanım veya business logic ilgili fazdan önce eklenmeyecek.</p>
    </section>
  </>
}
