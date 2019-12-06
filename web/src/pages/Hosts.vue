<template>
  <div class="section">
    <datatable title="Models" :data="events" :actions="datatableActions">
      <p slot="header" class="is-size-5">
        Hosts
      </p>
      <column slot="columns" display="Hostname" field="hostname" sortable="true"/>
      <column slot="columns" display="IP" field="ip" sortable="true"/>
      <column slot="columns" display="Models" field="models" sortable="true"/>
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
      datatableActions: [
        { content: 'Show models', handle: this.showModels, color: 'info' }
      ],
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

    console.log('about to fetch')
    fetch('http://' + process.env.BACKEND_URL + '/api/v1/hosts')
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
        }
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
    },

    /**
     * Show model info
     */
    showModels(host) {
      this.$router.push({
        name: 'home',
        params: {
          ip: host.ip
        }
      })
    }
  }
}
</script>
