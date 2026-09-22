import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface Attachment {
  name: string;
  type: 'pdf' | 'doc' | 'image';
  size?: string;
}

export interface RequisitionItem {
  id: number;
  no: number;
  partName: string;
  spec: string;
  position: string;
  makerName: string;
  qty: number;
  unit: string;
  remark: string;
  isUrgent: boolean;
  attachments?: Attachment[];
  // Detail for M/M
  machineModel: string;
  machineMaker: string;
  serialNo: string;
  // Detail for P/H (Procurement)
  acCode: string;
  vendor: string;
  unitPrice: number | null;
  currency: string;
  crCode: string;
  quotationNo: string;
  quotationPdf?: string;
  leadTime: string;
  vendor2?: string;
  status: 'Waiting Quotation' | 'Quoted' | 'Approved' | 'PO Issued';
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  // Document Metadata
  docNumber = 'DOC-2026-0901-003';
  docDate = '01/09/2026 15:45';
  requestBy = 'SIRIRAT SANGUANHONG';
  division = 'GM1';
  section = 'M/M';
  priority = 'URGENT';
  priorityReason = 'SPARE STORE of TAG on [ A1030-901 ] -3';
  orderType = 'Spare Part M/C';
  orderTypeDesc = 'อะไหล่ ของเครื่องจักร (ถ้าไม่มีใช้เครื่องจักรทำงานไม่ได้)';
  
  purchasers = [
    { name: 'NATTHANICHA SONTHIKESORN', initials: 'NS', role: 'Buyer Lead' },
    { name: 'SUNAN SRISOD', initials: 'SS', role: 'Senior Buyer' },
    { name: 'TICHAGORN PROMJAREE', initials: 'TP', role: 'Buyer' },
    { name: 'ANUSARA KUEADET', initials: 'AK', role: 'Procurement' },
    { name: 'CHANTHANY THAI', initials: 'CT', role: 'Procurement' },
    { name: 'PEERAPAT BUASA', initials: 'PB', role: 'Coordinator' },
    { name: 'KUNLADA PANMAN', initials: 'KP', role: 'Expeditor' }
  ];
  
  ccList = '-';

  // Search & Filters
  searchTerm = '';
  activeFilter: 'ALL' | 'URGENT' | 'WAITING' | 'QUOTED' = 'ALL';
  selectedItem: RequisitionItem | null = null;
  isDrawerOpen = false;
  isPdfModalOpen = false;
  activePdfTitle = '';
  activePdfName = '';
  toastMessage = '';
  toastVisible = false;

  // Items from the document screenshot
  items: RequisitionItem[] = [
    {
      id: 1,
      no: 1,
      partName: 'CONNECT AXIS DEVEC',
      spec: 'ST8101300',
      position: '-',
      makerName: 'FEDEX',
      qty: 5,
      unit: 'PCS',
      remark: '2008819 Ref.Last qtt for issue pr fitst(Q-NMB240901)',
      isUrgent: false,
      attachments: [
        { name: '2008819_Ref.pdf', type: 'pdf', size: '245 KB' }
      ],
      machineModel: 'HGM10152N / PMM F-4 / BROKEN',
      machineMaker: 'BM16#34',
      serialNo: '1231',
      acCode: '6218-G',
      vendor: 'LNS',
      unitPrice: null,
      currency: 'BT',
      crCode: 'TX',
      quotationNo: '260902-150926-ST8101300.pdf',
      quotationPdf: '260902-150926-ST8101300.pdf',
      leadTime: '20-25 DAYS',
      vendor2: '',
      status: 'Quoted'
    },
    {
      id: 2,
      no: 2,
      partName: 'FILTER',
      spec: 'FOR CLEANVY (FVH4-3856V2CV)',
      position: '-',
      makerName: 'CLEANVY',
      qty: 2,
      unit: 'PCS',
      remark: '2108146/22222ZS | Ref.Last qtt for issue pr fitsy',
      isUrgent: false,
      attachments: [
        { name: '20250428140628.pdf', type: 'pdf', size: '1.2 MB' }
      ],
      machineModel: 'HGG11166N / PMM F-1 / DIRTY',
      machineMaker: 'Cleanvy#02',
      serialNo: 'A06-026',
      acCode: '6218-G',
      vendor: 'IPO',
      unitPrice: null,
      currency: 'BT',
      crCode: '-',
      quotationNo: 'WAIT',
      quotationPdf: undefined,
      leadTime: 'Pending',
      vendor2: 'SIAM OHGITANI (2108146)',
      status: 'Waiting Quotation'
    },
    {
      id: 3,
      no: 3,
      partName: 'DISTILLATION COIL',
      spec: 'COIL-200L (INSIDE) /FVH4-3856V2CV',
      position: 'INSIDE',
      makerName: 'CLEANVY',
      qty: 3,
      unit: 'PCS',
      remark: '2108146/22222ZS (Ref.po:G33602A) Ref.Last price for issue pr first(27,000bt) (Q202410-002NMBT)',
      isUrgent: true,
      attachments: [],
      machineModel: 'HGG12643N / PMM F-1 / DEFECT',
      machineMaker: 'Cleanvy#02',
      serialNo: 'A06-026',
      acCode: '6218-G',
      vendor: 'IPO',
      unitPrice: 27000,
      currency: 'BT',
      crCode: '-',
      quotationNo: 'WAIT',
      quotationPdf: undefined,
      leadTime: 'Pending',
      vendor2: 'SIAM OHGITANI (2108146)',
      status: 'Waiting Quotation'
    },
    {
      id: 4,
      no: 4,
      partName: 'DISTILLATION COIL',
      spec: 'COIL-200L (OUTSIDE) /FVH4-3856V2CV',
      position: 'OUTSIDE',
      makerName: 'CLEANVY',
      qty: 3,
      unit: 'PCS',
      remark: '2108146/22222ZS (Ref.po:G33603A) Ref.Last price for issue pr first(27,000bt) (Q202410-002NMBT)',
      isUrgent: true,
      attachments: [],
      machineModel: 'HGG12644N / PMM F-1 / DEFECT',
      machineMaker: 'Cleanvy#02',
      serialNo: 'A06-026',
      acCode: '6218-G',
      vendor: 'IPO',
      unitPrice: 27000,
      currency: 'BT',
      crCode: '-',
      quotationNo: 'WAIT',
      quotationPdf: undefined,
      leadTime: 'Pending',
      vendor2: 'SIAM OHGITANI (2108146)',
      status: 'Waiting Quotation'
    }
  ];

  // KPIs
  get totalItems(): number {
    return this.items.length;
  }

  get totalQty(): number {
    return this.items.reduce((acc, item) => acc + (item.qty || 0), 0);
  }

  get urgentCount(): number {
    return this.items.filter(i => i.isUrgent).length;
  }

  get pendingQuotationCount(): number {
    return this.items.filter(i => i.quotationNo === 'WAIT' || !i.quotationPdf).length;
  }

  get filteredItems(): RequisitionItem[] {
    return this.items.filter(item => {
      // Filter tab
      if (this.activeFilter === 'URGENT' && !item.isUrgent) return false;
      if (this.activeFilter === 'WAITING' && item.status !== 'Waiting Quotation') return false;
      if (this.activeFilter === 'QUOTED' && item.status !== 'Quoted') return false;

      // Search
      if (!this.searchTerm.trim()) return true;
      const term = this.searchTerm.toLowerCase();
      return (
        item.partName.toLowerCase().includes(term) ||
        item.spec.toLowerCase().includes(term) ||
        item.makerName.toLowerCase().includes(term) ||
        item.machineModel.toLowerCase().includes(term) ||
        item.machineMaker.toLowerCase().includes(term) ||
        item.serialNo.toLowerCase().includes(term) ||
        item.vendor.toLowerCase().includes(term) ||
        (item.remark && item.remark.toLowerCase().includes(term))
      );
    });
  }

  setFilter(filter: 'ALL' | 'URGENT' | 'WAITING' | 'QUOTED'): void {
    this.activeFilter = filter;
  }

  openDrawer(item: RequisitionItem): void {
    // Clone to avoid immediate direct mutation before save
    this.selectedItem = JSON.parse(JSON.stringify(item));
    this.isDrawerOpen = true;
  }

  closeDrawer(): void {
    this.isDrawerOpen = false;
    this.selectedItem = null;
  }

  saveItemChanges(): void {
    if (!this.selectedItem) return;
    const index = this.items.findIndex(i => i.id === this.selectedItem!.id);
    if (index !== -1) {
      this.items[index] = { ...this.selectedItem };
      this.showToast(`บันทึกการแก้ไขรายการที่ ${this.selectedItem.no} เรียบร้อยแล้ว`);
    }
    this.closeDrawer();
  }

  toggleUrgent(item: RequisitionItem, event: MouseEvent): void {
    event.stopPropagation();
    item.isUrgent = !item.isUrgent;
    this.showToast(item.isUrgent ? `กำหนดให้รายการ #${item.no} เป็น URGENT แล้ว` : `ยกเลิกสถานะเร่งด่วนของรายการ #${item.no}`);
  }

  openPdfPreview(fileName: string, title?: string, event?: MouseEvent): void {
    if (event) event.stopPropagation();
    this.activePdfName = fileName;
    this.activePdfTitle = title || `เอกสาร: ${fileName}`;
    this.isPdfModalOpen = true;
  }

  closePdfModal(): void {
    this.isPdfModalOpen = false;
    this.activePdfName = '';
  }

  addNewItem(): void {
    const nextNo = this.items.length + 1;
    const newItem: RequisitionItem = {
      id: Date.now(),
      no: nextNo,
      partName: 'NEW SPARE PART',
      spec: 'SPECIFICATION DETAILS',
      position: '-',
      makerName: 'GENERIC',
      qty: 1,
      unit: 'PCS',
      remark: 'New requisition item',
      isUrgent: false,
      machineModel: 'LINE 1 / PMM',
      machineMaker: 'MAKER',
      serialNo: 'SN-000',
      acCode: '6218-G',
      vendor: 'IPO',
      unitPrice: null,
      currency: 'BT',
      crCode: '-',
      quotationNo: 'WAIT',
      leadTime: 'Pending',
      status: 'Waiting Quotation'
    };
    this.items.push(newItem);
    this.showToast(`เพิ่มรายการใหม่ #${nextNo} แล้ว`);
    this.openDrawer(newItem);
  }

  saveEntireDocument(): void {
    this.showToast('บันทึกข้อมูลเอกสาร Requisition ทั้งหมดสำเร็จ');
  }

  exportData(): void {
    this.showToast('กำลังดาวน์โหลดรายงานข้อมูล Excel...');
  }

  showToast(message: string): void {
    this.toastMessage = message;
    this.toastVisible = true;
    setTimeout(() => {
      this.toastVisible = false;
    }, 3200);
  }
}
