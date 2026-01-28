const grid = document.getElementById('grid')
const stats = document.getElementById('stats')
const searchInput = document.getElementById('search')
const filterButtons = document.querySelectorAll('[data-filter]')

let assets = []
let activeFilter = 'all'

function renderStats(data) {
  const svgCount = data.filter((asset) => asset.type === 'svg').length
  const pngCount = data.filter((asset) => asset.type === 'png').length
  stats.innerHTML = `
    <div class="stat">${data.length} total assets</div>
    <div class="stat">${svgCount} SVG assets</div>
    <div class="stat">${pngCount} PNG assets</div>
  `
}

function renderGrid(data) {
  grid.innerHTML = ''
  data.forEach((asset) => {
    const card = document.createElement('article')
    card.className = 'card'

    const sizeText = asset.size?.width && asset.size?.height
      ? `${asset.size.width} × ${asset.size.height}`
      : '—'

    card.innerHTML = `
      <div class="preview">
        <img src="${asset.path}" alt="${asset.name}" />
      </div>
      <div class="meta">
        <span class="badge">${asset.type.toUpperCase()}</span>
        <h3>${asset.name}</h3>
        <p>${asset.usage || '—'}</p>
        <small>Section: ${asset.section || '—'}</small>
        <small>Size: ${sizeText}</small>
        <small>Node: ${asset.sourceNodeId || '—'}</small>
      </div>
    `
    grid.appendChild(card)
  })
}

function applyFilters() {
  const query = searchInput.value.toLowerCase().trim()
  const filtered = assets.filter((asset) => {
    const matchesFilter = activeFilter === 'all' || asset.type === activeFilter
    const matchesQuery =
      !query ||
      asset.name.toLowerCase().includes(query) ||
      (asset.usage || '').toLowerCase().includes(query) ||
      (asset.section || '').toLowerCase().includes(query)
    return matchesFilter && matchesQuery
  })

  renderGrid(filtered)
}

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    filterButtons.forEach((btn) => btn.classList.remove('active'))
    button.classList.add('active')
    activeFilter = button.dataset.filter
    applyFilters()
  })
})

searchInput.addEventListener('input', applyFilters)

fetch('data/assets.json')
  .then((res) => res.json())
  .then((data) => {
    assets = data.assets || []
    renderStats(assets)
    applyFilters()
  })
  .catch((err) => {
    console.error('Failed to load assets.json', err)
    grid.innerHTML = '<p>Failed to load assets list. Run the export script first.</p>'
  })
