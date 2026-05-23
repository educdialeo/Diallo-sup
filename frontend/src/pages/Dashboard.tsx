import { PagePlaceholder } from '../components/PagePlaceholder'
import { StatusPill } from '../components/StatusPill'

export function Dashboard() {
  return (
    <PagePlaceholder
      title="Dashboard global"
      description="Vue d'ensemble de la flotte d'établissements supervisés."
    >
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <StatusPill status="ok" label="Santé OK" />
        <StatusPill status="warning" label="Warning" />
        <StatusPill status="critical" label="Critique" />
      </div>
      <button
        type="button"
        className="mt-6 rounded-lg bg-craie-400 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-craie-500"
      >
        Action primaire (démo charte)
      </button>
    </PagePlaceholder>
  )
}
