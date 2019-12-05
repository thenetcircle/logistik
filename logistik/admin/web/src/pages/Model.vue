<template>
  <div class="section">
    <!-- Rooms table -->
    <datatable title="Models" :data="events" :actions="datatableActions">
      <p slot="header" class="is-size-5">
        Models
        <a class="button is-primary is-small"><span class="icon"><i class="fa fa-plus"></i></span></a>
      </p>
      <column slot="columns" display="Event" field="event" sortable="true"/>
      <column slot="columns" display="Name" field="name" sortable="true"/>
      <column slot="columns" display="Mpde" field="node" sortable="true"/>
      <column slot="columns" display="Hostname" field="hostname" sortable="true"/>
      <column slot="columns" display="Port" field="port" sortable="true"/>
      <column slot="columns" display="Path" field="path" sortable="true"/>
    </datatable>
  </div>
</template>

<script>
// import { cloneDeep } from 'lodash/lang'
import Datatable from '@/components/Datatable'
import Column from '@/components/Column'
import Modal from '@/components/Modal'
import Loading from '@/components/Loading'
import Tooltip from '@/components/Tooltip'
import globalLoading from '@/mixins/globalLoading'
import doubleCheckDestroy from '@/mixins/doubleCheckDestroy'
// import * as actions from '@/store/actions'

export default {
  mixins: [globalLoading, doubleCheckDestroy],
  components: { Datatable, Column, Modal, Loading, Tooltip },
  data () {
    return {
      events: [],
      modalOpen: false,
      loading: { name: false, destroying: false }
    }
  },
  computed: {
  },
  created () {
  },
  mounted() {
    this.resetModal()
    const self = this

    window.addEventListener('keydown', (e) => {
      const key = e.which || e.keyCode

      if (key === 39) { // right
        self.currentClaim++
        if (self.currentClaim >= self.claims.length) {
          self.currentClaim = self.claims.length - 1
          return
        }
        self.fetchImage(self.claims[self.currentClaim].id)
      }
      else if (key === 37) { // left
        self.currentClaim--
        if (self.currentClaim < 0) {
          self.currentClaim = 0
          return
        }
        self.fetchImage(self.claims[self.currentClaim].id)
      }
    })

    fetch('http://localhost:5656/api/v1/models')
      .then((response) => {
          if (response.status !== 200) {
            console.log('Looks like there was a problem. Status Code: ' +
              response.status)
            return
          }

          response.json().then((data) => {
            console.log(data.data)
            self.events = data.data
          })
        },
      )
      .catch((err) => {
        console.log('Fetch Error :-S', err)
      })
  },
  methods: {
    /**
     * Reset modal stuff after close.
     */
    resetModal () {
      this.resetDestroying()
    },

    /**
     * Callback on modal close.
     * (From modal internal)
     */
    onModalClose () {
      this.closeModal()
      this.resetModal()
    },

    /**
     * Close modal.
     * (From outside)
    */
    closeModal () {
      this.modalOpen = false
    }
  }
}
</script>
