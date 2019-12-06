const meta = {}

document.querySelectorAll('meta').forEach((item) => {
  if (item.name) {
    meta[item.name] = item.content
  }
})

if (meta.base !== undefined && !meta.base.startsWith('/')) {
  meta.base = `/${meta.base}`
}
export default {
  serviceName: 'LogistikAdmin',
  base: '/',
  ...meta
}
