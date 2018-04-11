<template>
  <div class="section">
  </div>
</template>

<script>
import { cloneDeep } from 'lodash/lang';
import Datatable from '@/components/Datatable';
import Modal from '@/components/Modal';
import Loading from '@/components/Loading';
import Tooltip from '@/components/Tooltip';
import globalLoading from '@/mixins/globalLoading';
import doubleCheckDestroy from '@/mixins/doubleCheckDestroy';
import * as actions from '@/store/actions';

export default {
  mixins: [globalLoading, doubleCheckDestroy],
  components: { Datatable, Column, Modal, Loading, Tooltip },
  data() {
    return {
      modalOpen: false,
      loading: { name: false, destroying: false }
    };
  },
  computed: {
  },
  created() {
  },
  mounted() {
    this.resetModal();
  },
  methods: {
    /**
     * Reset modal stuff after close.
     */
    resetModal() {
      this.resetDestroying();
    },

    /**
     * Callback on modal close.
     * (From modal internal)
     */
    onModalClose() {
      this.closeModal();
      this.resetModal();
    },

    /**
     * Close modal.
     * (From outside)
    */
    closeModal() {
      this.modalOpen = false;
    },
  },
};
</script>
