import Vue from 'vue'
import Router from 'vue-router'
import Main from '@/pages/Main'
import Model from '@/pages/Model'
import Stats from '@/pages/Stats'
import Query from '@/pages/Query'
import Hosts from '@/pages/Hosts'
import Logs from '@/pages/Logs'
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
        { path: 'query', name: 'query', component: Query },
        { path: 'stats', name: 'stats', component: Stats },
        { path: 'hosts', name: 'hosts', component: Hosts },
        { path: 'logs', name: 'logs', component: Logs }
      ]
    },
    {
      path: '*',
      redirect: { name: 'home' }
    }
  ]
})

export default router
