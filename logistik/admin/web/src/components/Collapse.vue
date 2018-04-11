<template>
  <div class="collapse">
    <slot></slot>
  </div>
</template>

<script>
export default {
  props: {
    accordion: Boolean,
  },
  computed: {
    $collapseItems() {
      return this.$children.filter(child => child.isCollapseItem);
    },
  },
  methods: {
    openByIndex(index) {
      if (this.accordion) {
        this.$collapseItems.forEach((item, i) => {
          if (i !== index) {
            item.disactive();
          }
        });
      }
    },
  },
};
</script>

