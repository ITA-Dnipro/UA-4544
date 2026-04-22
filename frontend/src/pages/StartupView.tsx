import { useParams } from 'react-router-dom'

export default function StartupView() {
  const { id } = useParams()
  return <h1>Startup #{id}</h1>
}

