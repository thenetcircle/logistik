<template>
  <div class="datatable">
    <slot name="columns"></slot>
    <div class="datatable-header">
      <div class="datatable-header__content">
        <slot name="header"></slot>
      </div>
      <div class="datatable-header__search" v-if="searchable">
        <input class="input" type="text" placeholder="search" v-model="searchInput">
        <span class="icon is-small is-right"><i class="fa fa-search"></i></span>
      </div>
    </div>
    <div class="datatable-content">
      <table class="table is-fullwidth">
        <thead>
          <tr>
            <td v-for="(column, index) of columns" :key="index"
                :class="(column.sortable ? 'sortable ' : '') +
                        (sortedColumn === index ? (sortType === 'desc' ? 'sorting-desc' : 'sorting-asc') : '')"
                @click="sort(index)"
                :style="{ width: column.width || 'auto' }">
              {{ column.display }}
              <!-- Sortable icon -->
              <span v-if="column.sortable" class="icon is-tiny">
                <i class="fa fa-chevron-down"></i>
              </span>
            </td>
            <td class="actions-column" v-if="actions.length"></td>
          </tr>
        </thead>
        <tr v-if="!processedRows.length">
          <td class="has-text-centered" :colspan="columns.length + (actions.length ? 1 : 0)">No {{title}}</td>
        </tr>
        <transition-group tag="tbody" :css="false" @before-enter="beforeTrEnter" @enter="trEnter" @leave="trLeave">
          <tr v-for="(row, index) of paginated" :key="index" :data-index="index">
            <td v-for="(column, i) of columns" :key="i">{{ getColumnShownData(row, column) }}</td>
            <td class="actions-column" v-if="actions.length">
              <a v-html="action.content" v-for="(action, m) of actions" :key="m" @click="action.handle(row, index)" class="button action" :class="'is-' + (action.color || 'default')">
              </a>
            </td>
          </tr>
        </transition-group>
      </table>
    </div>
    <div class="datatable-footer" v-if="paginate">
      <div class="datatable-footer__pagesize">
        <span>Rows per page: </span>
        <div class="select is-small">
          <select v-model="currentPerPage">
            <option v-for="(option, index) in perPageOptions" :key="index" :value="option" :selected="option == currentPerPage">
                {{ option === -1 ? 'All' : option }}
            </option>
          </select>
        </div>
      </div>
      <div class="datatable-footer__itemcount">
          {{(currentPage - 1) * currentPerPage ? (currentPage - 1) * currentPerPage : 1}} -{{Math.min(processedRows.length, currentPerPage * currentPage)}} of {{processedRows.length}}
      </div>
      <div class="datatable-footer__pagination">
        <a class="pagination-button prev" @click="prevPage">
          <span class="icon is-small">
            <i class="fa fa-chevron-left"></i>
          </span>
        </a>
        <a class="pagination-button next" @click="nextPage">
          <span class="icon is-small">
            <i class="fa fa-chevron-right"></i>
          </span>
        </a>
      </div>
    </div>
  </div>
</template>
<script>
import Fuse from 'fuse.js'
import { head } from 'lodash/array'
import anime from 'animejs'

export default {
  props: {
    title: { required: true, type: String },
    data: { required: true, type: Array },
    actions: { type: Array, default: () => [] },
    perPage: { type: Array, default: () => [50, 100] },
    defaultPerPage: { type: Number, default: 50 },
    paginate: { type: Boolean, default: true },
    searchable: { type: Boolean, default: true }
  },
  data () {
    return {
      currentPage: 1,
      currentPerPage: 10,
      sortedColumn: -1,
      sortType: 'desc',
      searchInput: ''
    }
  },
  computed: {
    /**
     * The columns that will be shown in the table.
     *
     * @var {Array}
     */
    columns () {
      return this.$slots.columns.map(({ data: { attrs } }) => attrs)
    },

    /**
     * Options for how much data will be shown per page.
     *
     * @var {Array}
     */
    perPageOptions () {
      let options = this.perPage || [10, 20, 30, 40, 50]
      // Force numbers
      options = options.map(v => parseInt(v, 10))
      // Sort options
      options.sort((a, b) => a - b)
      // And add "All"
      options.push(-1)
      // If defaultPerPage is provided and it's a valid option, set as current per page
      if (options.indexOf(this.defaultPerPage) > -1) {
        // eslint-disable-next-line vue/no-side-effects-in-computed-properties
        this.currentPerPage = this.defaultPerPage
      }
      return options
    },

    /**
     * The rows of current page.
     *
     * @var {Array}
     */
    paginated () {
      let paginatedRows = this.processedRows
      if (this.paginate) {
        paginatedRows = paginatedRows.slice(
          (this.currentPage - 1) * this.currentPerPage,
          this.currentPerPage === -1 ? paginatedRows.length + 1 : this.currentPage * this.currentPerPage
        )
      }
      return paginatedRows
    },

    /**
     * The row after caculating(searching, sorting, etc.)
     *
     * @var {Array}
     */
    processedRows () {
      if (this.data.length === 0) {
        return []
      }

      let computedRows = this.data
      computedRows = computedRows.sort((x, y) => {
        if (!this.columns[this.sortedColumn]) {
          return 0
        }
        const column = this.columns[this.sortedColumn]

        const cook = (src) => {
          let dest = this.getColumnData(src, column.field)
          if (typeof dest === 'string') {
            dest = dest.toLowerCase()
            if (column.numeric) {
              dest = dest.indexOf('.') !== -1 ? parseFloat(dest) : parseInt(dest, 10)
            }
          }

          return dest
        }
        const cookedX = cook(x)
        const cookedY = cook(y)
        const m = cookedX < cookedY ? -1 : 1
        const n = this.sortType === 'desc' ? -1 : 1

        return m * n
      })

      // Show search result
      if (this.searchInput) {
        const searchConfig = { keys: Object.keys(head(computedRows)), minMatchCharLength: 2 }

        // Enable searching of numbers (non-string)
        // Temporary fix of https://github.com/krisk/Fuse/issues/144
        searchConfig.getFn = (obj, path) => {
          if (Number.isInteger(obj[path])) {
            return JSON.stringify(obj[path])
          }
          return obj[path]
        }

        if (this.exactSearch) {
          // return only exact matches
          searchConfig.threshold = 0
          searchConfig.distance = 0
        }

        computedRows = (new Fuse(computedRows, searchConfig)).search(this.searchInput)
      }
      // eslint-disable-next-line vue/no-side-effects-in-computed-properties
      this.currentPage = 1
      return computedRows
    }
  },
  methods: {

    /**
     * Go to previout page.
     */
    prevPage () {
      if (this.currentPage > 1) {
        this.currentPage -= 1
      }
    },

    /**
     * Go to next page.
     */
    nextPage () {
      if (this.processedRows.length > this.currentPerPage * this.currentPage) {
        this.currentPage += 1
      }
    },

    /**
     * Get the data from one row of given column.
     *
     * @param {Object} src
     * @param {any} field
     * @return {String}
     */
    getColumnData (src, field) {
      if (typeof field === 'function') {
        return field(src)
      } else if (typeof field === 'string') {
        return this.dig(src, field)
      }
      return ''
    },

    /**
     * Get the data for displaying. especially convert number to locale string.
     *
     * @param {Object} src
     * @param {any} column
     * @return {String}
     */
    getColumnShownData (src, column) {
      let result = this.getColumnData(src, column.field)

      if (column.numeric) {
        if (typeof result === 'string') {
          result = result.indexOf('.') !== -1 ? parseFloat(result) : parseInt(result, 10)
        }

        if (column.locale) {
          result = result.toLocaleString()
        }
      }
      return result
    },

    /**
     * Recursively get the attribute form an object by `.` splited key.
     *
     * @param {Object} obj
     * @param {String} path
     * @return {Object}
     */
    dig (obj, path) {
      let result = obj
      const splitter = path.split('.')

      splitter.forEach((item) => {
        if (result !== undefined) {
          result = result[item]
        }
      })

      return result
    },

    /**
     * Sorting by clicked column.
     *
     * @param {Number} index
     */
    sort (index) {
      if (!this.columns[index].sortable) {
        return
      }
      if (this.sortedColumn === index) {
        this.sortType = this.sortType === 'desc' ? 'asc' : 'desc'
      } else {
        this.sortedColumn = index
        this.sortType = 'desc'
      }
    },

    /**
     * Set property before table row enter.
     *
     * @param {HTMLTrElement} el
     */
    beforeTrEnter (el) {
      el.style.setProperty('opacity', 0)
    },

    /**
     * show enter animation.
     *
     * @param {HTMLTrElement} el
     * @param {Function} done
     */
    trEnter (el, done) {
      const delay = el.dataset.index * 100
      anime({
        targets: el,
        delay,
        opacity: 1,
        complete: done
      })
    },

    /**
     * Show leave animation.
     *
     * @param {HTMLTrElement} el
     * @param {Function} done
     */
    trLeave (el, done) {
      anime({
        targets: el,
        delay: el.dataset.index * 100,
        opacity: 0,
        easing: 'easeInOutQuart',
        duration: 300,
        complete: done
      })
    }
  }
}
</script>
