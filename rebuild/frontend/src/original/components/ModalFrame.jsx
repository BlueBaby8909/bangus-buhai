import { useEffect, useRef } from 'react'
export default function ModalFrame({ children, onClose, label }) {
  const dialogRef=useRef(null)
  useEffect(()=>{
    const dialog=dialogRef.current
    const previous=document.activeElement
    dialog.showModal()
    return ()=>{dialog.close();if(previous?.isConnected) previous.focus()}
  },[])
  function keepFocusInDialog(event) {
    if(event.key!=='Tab') return
    const controls=[...dialogRef.current.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]')]
      .filter((element)=>element.getClientRects().length>0)
    const first=controls[0], last=controls[controls.length-1]
    if(event.shiftKey && document.activeElement===first){event.preventDefault();last?.focus()}
    else if(!event.shiftKey && document.activeElement===last){event.preventDefault();first?.focus()}
  }
  return <dialog ref={dialogRef} aria-label={label} onKeyDown={keepFocusInDialog} onCancel={(event)=>{event.preventDefault();onClose()}} className={`sample-dialog ${label.includes('prediction') ? 'sample-dialog-wide' : ''}`}>{children}</dialog>
}
