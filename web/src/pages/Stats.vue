<template>
  <div class="section">
    <datatable title="Stats" :data="stats" :actions="datatableActions">
      <p slot="header" class="is-size-5">
        Model Statistics
      </p>
      <column slot="columns" display="Requests" field="requests" sortable="true"/>
      <column slot="columns" display="Exceptions" field="exceptions" sortable="true"/>
      <column slot="columns" display="Running Time" field="running_time" sortable="true"/>
      <column slot="columns" display="Status" field="status" sortable="true"/>
      <column slot="columns" display="Load" field="load" sortable="true"/>
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
  data() {
    return {
      stats: [],
      modalOpen: false,
      datatableActions: [],
      loading: { name: false, destroying: false }
    }
  },
  computed: {
    identity() {
      return this.$route.params.identity
    }
  },
  created() {
  },
  mounted() {
    this.resetModal()
    this.showGlobalLoading()
    const self = this

    fetch('http://' + process.env.ROOT_API + '/api/v1/stats/' + self.identity, {method: 'get'})
      .then((response) => {
        self.hideGlobalLoading()
        if (response.status !== 200) {
          console.log('Looks like there was a problem. Status Code: ' + response.status)
          return
        }

        response.json().then((data) => {
          self.stats = [data.data]
        })
      })
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
