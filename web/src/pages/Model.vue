<template>
  <div class="section">
    <datatable title="Models" :data="events" :actions="datatableActions">
      <p slot="header" class="is-size-5">
        Models
      </p>
      <column slot="columns" display="Event" field="event" sortable="true"/>
      <column slot="columns" display="Name" field="name" sortable="true"/>
      <column slot="columns" display="Node" field="node" sortable="true"/>
      <column slot="columns" display="Hostname" field="hostname" sortable="true"/>
      <column slot="columns" display="Endpoint" field="endpoint" sortable="true"/>
      <column slot="columns" display="Port" field="port" sortable="true"/>
      <!--column slot="columns" display="Path" field="path" sortable="true"/-->
      <column slot="columns" display="Requests" field="requests" sortable="true"/>
      <column slot="columns" display="Exceptions" field="exceptions" sortable="true"/>
      <column slot="columns" display="Uptime" field="running_time" sortable="true"/>
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
  data () {
    return {
      events: [],
      modalOpen: false,
      datatableActions: [
        { content: 'Query', handle: this.queryModel, color: 'info' }
      ],
      loading: { name: false, destroying: false }
    }
  },
  computed: {
    ip() {
      return this.$route.params.ip
    }
  },
  created () {
  },
  mounted() {
    this.resetModal()
    const self = this

    let url = 'http://' + process.env.ROOT_API + '/api/v1/models'
    if (self.ip !== undefined) {
      url += '/ip/' + self.ip
    }

    fetch(url)
      .then((response) => {
          if (response.status !== 200) {
            console.log('Looks like there was a problem. Status Code: ' +
              response.status)
            return
          }

          response.json().then((data) => {
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

    queryModel(model) {
      this.$router.push({
        name: 'query',
        params: {
          identity: model.identity
        }
      })
    }
  }
}
</script>
