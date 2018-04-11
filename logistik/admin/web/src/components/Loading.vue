<template functional>
  <div class="loading-wrapper">
    <svg class="triangle-loading" viewBox="0 0 100 100">
      <path id="right"
            d="M 50,16 L 96,96"
            stroke-width="8"
            fill-opacity="0"
            stroke-dasharray="100"
            stroke-linecap="round"
            stroke-linejoin="round" ></path>
      <path id="bottom"
            d="M 96,96 L 4,96"
            stroke-width="8"
            fill-opacity="0"
            stroke-dasharray="100"
            stroke-linecap="round"
            stroke-linejoin="round" ></path>
      <path id="left"
            d="M 4,96 L 50,16"
            stroke-width="8"
            fill-opacity="0"
            stroke-dasharray="100"
            stroke-linecap="round"
            stroke-linejoin="round" ></path>

      <animate
        attributeName="stroke-dashoffset"
        dur="1.5s"
        d="fill"
        repeatCount="indefinite"
        keyTimes="0; 0.6; 0.6; 0.8;1"
        values="100; 0; 190; 108; 108" ></animate>
      <animate
        xlink:href="#bottom"
        attributeName="stroke-dashoffset"
        dur="1.5s"
        d="fill"
        repeatCount="indefinite"
        keyTimes="0; 0.6; 0.6; 0.8;1"
        values="100; 0; 190; 109; 109" ></animate>
    </svg>
  </div>
</template>
<script>
export default { };
</script>
