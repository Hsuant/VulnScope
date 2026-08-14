import { ref, computed } from 'vue'

export function usePagination(defaultPageSize = 20) {
  const page = ref(1)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  function onPageChange(p: number) {
    page.value = p
  }

  function onPageSizeChange(size: number) {
    pageSize.value = size
    page.value = 1
  }

  function reset() {
    page.value = 1
    total.value = 0
  }

  return { page, pageSize, total, totalPages, onPageChange, onPageSizeChange, reset }
}