<template>
  <div class="section" style="text-align:left">
    <p slot="header" class="is-size-5">
      Model logs
    </p>
    <pre>
      {{ lines }}
    </pre>
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
      lines: [],
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

    fetch('http://' + process.env.ROOT_API + '/api/v1/logs/' + self.identity, {method: 'get'})
      .then((response) => {
        self.hideGlobalLoading()
        if (response.status !== 200) {
          console.log('Looks like there was a problem. Status Code: ' + response.status)
          return
        }

        response.json().then((data) => {
          self.lines = data.data
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
