export default {
  data() {
    return {
      destroying: null,
    };
  },
  created() {
    this.resetDestroying();
  },
  methods: {
    /**
     * Reset double-checking destroying.
     */
    resetDestroying() {
      this.destroying = { item: '', id: null };
    },

    /**
     * All deleting associated stuff need double checking to finish the processing.
     * use {item} and {id} to ensure unique entity to be deleted.
     *
     * @param {string} item
     * @param {string} id
     * @returns {boolean}
     */
    doubleCheckDestroy(item, id) {
      if (this.destroying && this.destroying.id === id && this.destroying.item === item) {
        this.resetDestroying();
        return true;
      }
      this.destroying.id = id;
      this.destroying.item = item;
      this.$dialog.show('Click again to destroy!');
      return false;
    },
  },
};
