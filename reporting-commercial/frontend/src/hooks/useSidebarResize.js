import { useState, useCallback, useRef } from 'react'

export default function useSidebarResize(initialWidth = 256, minWidth = 160, maxWidth = 520) {
  const [sidebarWidth, setSidebarWidth] = useState(initialWidth)
  const sidebarDragging = useRef(false)

  const handleSidebarResizeStart = useCallback((e) => {
    e.preventDefault()
    sidebarDragging.current = true
    const startX = e.clientX
    const startWidth = sidebarWidth

    const onMouseMove = (e) => {
      if (!sidebarDragging.current) return
      setSidebarWidth(Math.min(Math.max(startWidth + (e.clientX - startX), minWidth), maxWidth))
    }

    const onMouseUp = () => {
      sidebarDragging.current = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [sidebarWidth, minWidth, maxWidth])

  return { sidebarWidth, setSidebarWidth, handleSidebarResizeStart }
}
