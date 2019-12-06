<template>
  <div class="section">
    <span v-for="(attachment, i) in response" v-bind:key="i">
      <span>{{ attachment.objectType }}</span>: <span>{{ attachment.content }}</span><br />
    </span>
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
      response: [],
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

    console.log('about to fetch')
    fetch('http://localhost:5656/api/v1/query/' + self.identity, {
        method: 'post',
        body: JSON.stringify({
          'version': '2.0',
          'actor': {
            'id': Math.floor(Math.random() * 1000000).toString(),
            'objectType': 'user'
            },
          'object': {
            'id': Math.floor(Math.random() * 1000000).toString(),
            'objectType': 'image',
            'url': 'http://8.bild.poppen.lab:7080/fsk16/8/D/8/1971-8D82A3763C66A5FA5A1078543B84EFB0.jpg'
          },
          'provider': {
            'id': 'poppen',
            'objectType': 'community'
          },
          'published': '2019-12-05T08:32:23Z',
          'title': 'image.nude_detect',
          'verb': 'nude_detect',
          'id': '76a734bb-60c3-4a78-8a34-d9a1d27c1237'
        })
      })
      .then((response) => {
        self.hideGlobalLoading()
        if (response.status !== 200) {
          console.log('Looks like there was a problem. Status Code: ' + response.status)
          return
        }

        response.json().then((data) => {
          if (data.data.object === undefined || data.data.object.attachments === undefined) {
            return
          }
          console.log(data.data)
          self.response = data.data.object.attachments
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
