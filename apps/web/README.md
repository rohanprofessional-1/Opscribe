# Opscribe Web (Frontend)

React + TypeScript frontend for designing and managing infrastructure diagrams. Dark-themed, with a **dashboard** (list of designs) and a **designer** (drag-and-drop canvas with nodes and edges).

## Running the app

```bash
npm install
npm run dev
```

Open http://localhost:5173. For production build: `npm run build` then `npm run preview`.

### API base URL

The app talks to the Opscribe API for persistence. Set the base URL via env:

- **Behind nginx** (e.g. `/api` proxied to the API): leave unset or set `VITE_API_URL=/api`.
- **Local dev** (frontend on 5173, API on 8000): set `VITE_API_URL=http://localhost:8000` (and ensure CORS allows the frontend origin).

Create a `.env` in `apps/web` if needed:

```
VITE_API_URL=http://localhost:8000
```

---

## High-level flow

- **Startup:** App loads → `GET /clients/anon/session` (get-or-create anonymous client) → `GET /clients/{clientId}/graphs` → dashboard shows the list of designs.
- **Create design:** User clicks “Create new design” → `POST /graphs` → open designer with the new graph id.
- **Open design:** User clicks a card → designer opens; if the id is a UUID and the design has no nodes in memory, it fetches `GET /graphs/{id}/visualize` and maps the response to the canvas.
- **Save:** User clicks Back in the designer → `PUT /graphs/{id}/sync` with current nodes, edges, and name.
- **Delete:** User clicks trash on a card → `DELETE /graphs/{id}` and the design is removed from the list.

---

## Main files

### Entry & app shell

| File               | Purpose                                                                                                                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`src/main.tsx`** | Vite/React entry; mounts the app and React strict mode.                                                                                                                                                |
| **`src/App.tsx`**  | Switches between **dashboard** and **designer**. Uses `useInfrastructureDesigns` for API-backed designs; on “Create new” calls `createDesignAsync()` and opens the designer when the graph is created. |

### API layer

| File                         | Purpose                                                                                                                                                                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`src/api/client.ts`**      | Fetch-based API client. Exposes `getAnonSession()`, `listGraphs(clientId)`, `createGraph()`, `getVisualization(graphId)`, `syncGraph(graphId, body)`, `deleteGraph(graphId)`. Uses `VITE_API_URL` (default `/api`) and `credentials: 'include'` for cookies. |
| **`src/types/apiFormat.ts`** | TypeScript types for API responses (`ClientRead`, `GraphRead`, `NodeRead`, `EdgeRead`, `GraphVisualization`).                                                                                                                                                |

### State & persistence

| File                                        | Purpose                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`src/hooks/useInfrastructureDesigns.ts`** | Hook that backs the dashboard and designer with the API. On mount: anon session → list graphs → sets `designs`. Exposes `designs`, `loading`, `error`, `createDesignAsync()`, `updateDesign(id, { name, nodes, edges })`, `deleteDesign(id)`, `getDesign(id)`. Saving is done via `PUT /graphs/{id}/sync`. |

### Domain types & static data

| File                              | Purpose                                                                                                                                                    |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`src/types/infrastructure.ts`** | Domain types: `NodeCategory`, per-category node data, `InfrastructureNodeData`, `NodeTemplate`, `CategoryConfig`, `InfrastructureDesign`, dashboard props. |
| **`src/data/nodeTemplates.ts`**   | Palette config: `categories`, `nodeTemplates`, `getCategoryColor()`. Defines which nodes (SQL DB, Cache, VPC, etc.) appear in the left panel.              |

### Pages

| File                                             | Purpose                                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`src/components/InfrastructureDashboard.tsx`** | Dashboard: grid of “Create new design” (plus) and one card per design (name, updated date). Handles loading/error and create-pending state. Click card → open design; click trash → delete.                                                                                                                          |
| **`src/components/InfrastructureDesigner.tsx`**  | Designer: left palette, center React Flow canvas, right properties panel. Loads nodes/edges from `GET /graphs/{id}/visualize` when opening a graph by UUID with no nodes in memory. On Back, calls `onBack(nodes, edges, name)` which triggers `syncGraph`. Supports edge selection and deletion (Backspace/Delete). |

### Designer sub-components

| File                                        | Purpose                                                                                                                                                         |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`src/components/NodePalette.tsx`**        | Left panel: searchable, collapsible categories and draggable node tiles; `onDragStart` passes the template for drop on the canvas.                              |
| **`src/components/InfrastructureNode.tsx`** | Custom React Flow node: category color, icon, label; source/target handles for edges.                                                                           |
| **`src/components/PropertiesPanel.tsx`**    | Right panel: when a node is selected, shows fields by category (database, compute, storage, networking, security, messaging); “Delete Node” and editable label. |

### Styles

| File                | Purpose                                                                                                                                 |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **`src/App.css`**   | Global dark-theme styles, scrollbars, and form utility classes (`.form-input`, `.form-select`, `.form-checkbox`). React Flow overrides. |
| **`src/index.css`** | Tailwind directives and base layout (full-height, overflow hidden).                                                                     |

---

## Where to put new code

- **Pages / layouts** → `src/components/`
- **Domain types** → `src/types/`
- **Static config / templates** → `src/data/`
- **API helpers / types** → `src/api/`, `src/types/apiFormat.ts`
- **Shared state / data loading** → `src/hooks/`
