// Tag management page (TagManageView.vue)
export default {
  createTag: 'New Tag',
  editTag: 'Edit Tag',
  searchPlaceholder: 'Search tag name or namespace...',
  noMatch: 'No matching tags',
  noTags: 'No tags',
  tryOtherKeywords: 'Try a different keyword',
  noneCreated: 'No tags created yet',
  columns: {
    color: 'Color',
    pocCount: 'POCs',
  },
  fields: {
    namespace: 'Namespace',
    tagName: 'Tag name',
    color: 'Color',
    description: 'Description',
  },
  placeholders: {
    namespace: 'Select or type a namespace',
    tagName: 'Tag name',
    description: 'Description',
  },
  rules: {
    namespace: 'Please enter a namespace',
    tagName: 'Please enter a tag name',
  },
  messages: {
    createSuccess: 'Tag created',
    updateSuccess: 'Tag updated',
    deleteSuccess: 'Tag deleted',
  },
}
