# React Best Practices
Source: vercel-labs/agent-skills · https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices
License: MIT · https://github.com/vercel-labs/agent-skills

## Overview

React patterns that produce maintainable, performant components.
These rules are based on the React team's recommendations and production experience.

## Component Design

### Prefer small, focused components

```tsx
// Bad: one component doing too much
const Dashboard = () => {
  const [users, setUsers] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  // 200 lines of JSX...
}

// Good: composed from focused components
const Dashboard = () => (
  <DashboardLayout>
    <StatsSummary />
    <UserList />
  </DashboardLayout>
)
```

### Colocate state with its consumer

State should live as close as possible to where it is used.
Lift state only when two siblings genuinely need to share it.

## Hooks

### useEffect — the most misused hook

```tsx
// Bad: missing dependency, causes stale closure
useEffect(() => {
  fetchUser(userId)
}, [])  // userId missing from deps

// Good: correct deps + cleanup
useEffect(() => {
  let cancelled = false
  fetchUser(userId).then(user => {
    if (!cancelled) setUser(user)
  })
  return () => { cancelled = true }
}, [userId])
```

### Never suppress the lint rule for exhaustive-deps

If the lint rule fires, fix the dependency — do not add `// eslint-disable`.

### Extract complex effects into custom hooks

```tsx
// Good: custom hook encapsulates the effect
function useUser(userId: string) {
  const [user, setUser] = useState<User | null>(null)
  useEffect(() => {
    let cancelled = false
    getUser(userId).then(u => { if (!cancelled) setUser(u) })
    return () => { cancelled = true }
  }, [userId])
  return user
}
```

## Performance

### Memoization — use sparingly

Memoization has a cost. Add it only when you have measured a real performance problem.

```tsx
// useMemo: expensive computation, many re-renders
const sorted = useMemo(
  () => items.sort((a, b) => a.name.localeCompare(b.name)),
  [items]
)

// useCallback: stable reference for child component props
const handleSelect = useCallback((id: string) => {
  setSelected(id)
}, [])  // no deps = stable reference
```

### Avoid anonymous functions in JSX

```tsx
// Bad: creates a new function every render
<Button onClick={() => handleClick(item.id)} />

// Good: stable reference
const handleItemClick = useCallback(() => handleClick(item.id), [item.id])
<Button onClick={handleItemClick} />
```

## Data Fetching

Use TanStack Query (React Query) for server state:

```tsx
import { useQuery } from "@tanstack/react-query"

function ItemList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["items"],
    queryFn: () => fetchItems(),
    staleTime: 60_000,  // cache for 1 minute
  })

  if (isLoading) return <Spinner />
  if (error) return <ErrorMessage error={error} />
  return <ul>{data.map(item => <ItemCard key={item.id} item={item} />)}</ul>
}
```

Do not use `useEffect` + `useState` for data fetching — it creates race conditions.

## TypeScript in React

```tsx
// Always type component props explicitly
interface ButtonProps {
  label: string
  onClick: () => void
  disabled?: boolean
  variant?: "primary" | "secondary"
}

// Never use React.FC — it adds implicit children prop
export const Button = ({ label, onClick, disabled = false }: ButtonProps) => (
  <button onClick={onClick} disabled={disabled}>{label}</button>
)
```

## Integration with DeepLocal Forge

```
/read skills/frontend/vercel-react-best-practices.md
/architect
Design a React component for: [description]

Apply these rules:
1. Single responsibility — one purpose per component
2. Correct useEffect dependencies
3. TanStack Query for server data
4. Typed props (no React.FC)
5. Tailwind for styling (no inline styles)

Output: component skeleton with types, no implementation logic yet.
Standards: see ai-specs/specs/frontend-standards.mdc
```
