/**
 * Attributes:
 *
 * id(parent only): unique id.
 * label:           the name which will be displayed
 * name:            name of the router will be navigated to after click
 * link:            if set, the name will be ignored, and directly visit the link.
 */
export default {
  items: [
    {
      id: 1,
      label: 'Logistik',
      children: [
        { name: 'home', label: 'Overview' },
        { name: 'model', label: 'Models' }
      ]
    }
  ]
}
