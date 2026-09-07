import { Link } from 'react-router-dom'
export default function ComingSoon({ title, forbidden = false }) {
  return <main><div className="eyebrow">LABELSURE / WORKSPACE</div><section className="panel future-panel"><span className="phase-badge">{forbidden ? 'ACCESS RESTRICTED' : 'PLANNED MODULE'}</span><h1>{title}</h1><p>{forbidden ? 'Your assigned role does not permit access to this page.' : 'Coming in a future implementation phase.'}</p><Link to="/dashboard" className="text-link">Return to dashboard →</Link></section></main>
}
