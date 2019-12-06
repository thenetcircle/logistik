import Vue from 'vue'
import Router from 'vue-router'
import Main from '@/pages/Main'
import Model from '@/pages/Model'
import Query from '@/pages/Query'
import config from '@/config'

Vue.use(Router)

const router = new Router({
  mode: 'history',
  routes: [
    {
      path: config.base,
      component: Main,
      children: [
        { path: config.base, name: 'home', component: Model },
        { path: 'query', name: 'query', component: Query }
      ]
    },
    {
      path: '*',
      redirect: { name: 'home' }
    }
  ]
})

export default router
