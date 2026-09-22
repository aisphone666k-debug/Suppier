import { Component, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, EmployeeUser } from './services/api.service';

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
  poRef?: string;
  isUrgent: boolean;
  attachments?: Attachment[];
  // Detail for M/M
  machineModel: string;
  machineMaker: string;
  serialNo: string;
  // Detail for P/H (Procurement)
  // Quotation 1
  acCode: string;
  vendor: string;
  unitPrice: number | null;
  currency: string;
  crCode: string;
  quotationNo: string;
  quotationPdf?: string;
  leadTime: string;
  // Quotation 2
  acCode2?: string;
  vendor2?: string;
  unitPrice2?: number | null;
  currency2?: string;
  crCode2?: string;
  quotationNo2?: string;
  quotationPdf2?: string;
  leadTime2?: string;
  status: 'Waiting Quotation' | 'Quoted' | 'Approved' | 'PO Issued';
  isEditing?: boolean;
  backupData?: any;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements AfterViewInit {
  // Authentication & OTP State
  isLoggedIn = false;
  otpCode = '';
  isInputFocused = true;
  loginError = '';
  loggedInEmployeeId = '';
  loginPhase: 'input' | 'rotating' | 'converging' | 'downloading' | 'success' | 'fail-converging' | 'shattered' = 'input';
  downloadPercent = 0;
  currentUser: EmployeeUser | null = null;

  constructor(private apiService: ApiService) {}

  ngAfterViewInit(): void {
    this.focusInput();
  }

  // Navigation & View State
  activeMenu = 'spare-part';
  activeView: 'list' | 'edit' = 'edit';
  
  // Left Sidebar Menus
  documentMenus: Array<{
    id: string;
    label: string;
    isExpanded?: boolean;
    subItems?: Array<{ id: string; label: string }>;
  }> = [
    { 
      id: 'kzw', 
      label: 'KZW',
      isExpanded: true,
      subItems: [
        { id: 'kzw-gm1', label: 'GM1' },
        { id: 'kzw-ma', label: 'MA' },
        { id: 'kzw-pma', label: 'PMA' }
      ]
    },
    { 
      id: 'made-to-order', 
      label: 'Made to order',
      isExpanded: true,
      subItems: [
        { id: 'mto-gm1', label: 'GM1' },
        { id: 'mto-ma', label: 'MA' },
        { id: 'mto-pma', label: 'PMA' }
      ]
    },
    { 
      id: 'repair', 
      label: 'Repair',
      isExpanded: true,
      subItems: [
        { id: 'repair-gm1', label: 'GM1' },
        { id: 'repair-ma', label: 'MA' },
        { id: 'repair-pma', label: 'PMA' }
      ]
    },
    { id: 'spare-part', label: 'Spare part (Oversea & Local)' },
    { id: 'made-to-maker', label: 'Made to maker' },
    { id: 'store-tooling', label: 'Store tooling' },
    { id: 'project', label: 'Project' },
    { id: 'maker-misumi', label: 'Maker Misumi' }
  ];
  activeSubMenu = '';

  masterMenus = [
    { id: 'master-section', label: 'Master Section' },
    { id: 'master-unit', label: 'Master Unit' },
    { id: 'master-order-type', label: 'Master Order Type' },
    { id: 'master-purchase', label: 'Master Purchase' },
    { id: 'master-access', label: 'Master Access' }
  ];

  // Document Tree Sample Rows
  quotationList = [
    { date: '08/06/2026 10:28', partName: 'DRY SCREW VACUUM PUMP', spec: 'SDV-30S', maker: 'SHCOH SANGYO', qty: 1, unit: 'PCS', vendor1: 'WORLD PUMP' },
    { date: '25/06/2026 15:46', partName: 'AIR CYLINDER', spec: 'ACQ100x115-S-B', maker: 'AIRTAC', qty: 1, unit: 'PCS', vendor1: 'AIRTAC 2060080' },
    { date: '06/08/2026 17:41', partName: 'FILTER', spec: 'MP5002-40WN-DOE(0.2UM 40")', maker: 'PEMIUM', qty: 1, unit: 'PCS', vendor1: 'IPO 22222ZS', isCurrentDoc: true },
    { date: '14/09/2026 12:18', partName: 'ROBO CYLINDER', spec: 'RCP2-SS7R-I-42P-12-200', maker: 'IAI', qty: 1, unit: 'PCS', vendor1: 'IPO 22222ZS' },
    { date: '21/09/2026 16:22', partName: 'AIR CYLINDER', spec: 'MGPL50-150A-Y59BL', maker: 'SMC', qty: 1, unit: 'PCS', vendor1: 'CHAVANAN' },
    { date: '21/09/2026 16:36', partName: 'CLAMP / REDUCER', spec: 'KQC-16 / KF16/25', maker: 'ULVAC', qty: 12, unit: 'PCS', vendor1: 'ULVAC' }
  ];

  // Document Metadata & Status
  docNumber = 'DOC-2026-0901-003';
  docDate = '06/08/2026 17:41';
  documentStatus = 'Waiting for purchase approve';
  requestBy = 'DANUPHON SUTTHIWATTHANAK';
  division = 'MA';
  section = 'M/M';
  priority = 'NORMAL';
  priorityReason = 'SPARE PART FOR UDI SYSTEM';
  orderType = 'Spare Part M/C';
  orderTypeDesc = 'อะไหล่ ของเครื่องจักร (ถ้าไม่มีใช้เครื่องจักรทำงานไม่ได้)';
  
  // Approval Information
  isApprovalExpanded = true;
  approvalComment = '';
  approvers = [
    { name: 'NATTHANICHA SONTHIKESORN', status: '', date: '' },
    { name: 'PEERAPAT BUASA', status: '', date: '' },
    { name: 'TICHAGORN PROMJAREE', status: '', date: '' },
    { name: 'SIRITORN KUSOLEIAM', status: '', date: '' },
    { name: 'KUNLADA PANMAN', status: '', date: '' },
    { name: 'THEERARAT NANTHAWISIT', status: '', date: '' },
    { name: 'ANUSARA KUEADET', status: '', date: '' },
    { name: 'CHANTHANY THAI', status: '', date: '' }
  ];

  getInitials(name: string): string {
    if (!name) return '';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  toggleMenu(menu: any, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    if (menu.subItems) {
      menu.isExpanded = !menu.isExpanded;
    }
  }

  selectMenu(menuId: string): void {
    this.activeMenu = menuId;
    this.activeSubMenu = '';
    const foundMenu = this.documentMenus.find(m => m.id === menuId);
    if (foundMenu?.subItems) {
      foundMenu.isExpanded = true;
    }
    if (menuId === 'spare-part') {
      this.activeView = 'edit';
    } else {
      this.activeView = 'list';
    }
  }

  selectSubMenu(parentMenu: any, subItem: { id: string; label: string }, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.activeMenu = parentMenu.id;
    this.activeSubMenu = subItem.id;
    this.division = subItem.label;
    this.activeView = 'edit';
  }

  openDocument(): void {
    this.activeView = 'edit';
  }

  closeDocument(): void {
    this.activeView = 'list';
  }

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
      position: '',
      makerName: 'FEDEX',
      qty: 5,
      unit: 'PCS',
      poRef: '2008819',
      remark: 'Ref.Last qtt for issue pr fitst(Q-NMB240901 )',
      isUrgent: false,
      attachments: [],
      machineModel: 'HGM10152N\n/ PMM F-4\n/ BROKEN',
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
      unitPrice2: null,
      status: 'Quoted'
    },
    {
      id: 2,
      no: 2,
      partName: 'FILTER',
      spec: 'FOR CLEANVY\n(FVH4-3856V2CV)',
      position: '',
      makerName: 'CLEANVY',
      qty: 2,
      unit: 'PCS',
      poRef: '2108146/22222ZS',
      remark: 'Ref.Last qtt for issue pr fitsy',
      isUrgent: false,
      attachments: [
        { name: '20250428140628.pdf', type: 'pdf', size: '1.2 MB' }
      ],
      machineModel: 'HGG11166N\n/ PMM F-1\n/ DIRTY',
      machineMaker: 'Cleanvy#02',
      serialNo: 'A06-026',
      acCode: '',
      vendor: 'IPO',
      unitPrice: null,
      currency: '',
      crCode: '',
      quotationNo: 'WAIT',
      quotationPdf: undefined,
      leadTime: '',
      vendor2: 'SIAM OHGITANI\n2108146',
      unitPrice2: null,
      status: 'Waiting Quotation'
    },
    {
      id: 3,
      no: 3,
      partName: 'DISTILLATION COIL',
      spec: 'COIL-200L\n(INSIDE)\n/FVH4-3856V2CV',
      position: '',
      makerName: 'CLEANVY',
      qty: 3,
      unit: 'PCS',
      poRef: '2108146/22222ZS\n(Ref.po:G33602A)',
      remark: 'Ref.Last price for issue pr first(27,000bt)\n(Q202410-002NMBT)',
      isUrgent: true,
      attachments: [],
      machineModel: 'HGG12643N\n/ PMM F-1\n/ DEFECT',
      machineMaker: 'Cleanvy#02',
      serialNo: 'A06-026',
      acCode: '',
      vendor: 'IPO',
      unitPrice: null,
      currency: '',
      crCode: '',
      quotationNo: 'WAIT',
      quotationPdf: undefined,
      leadTime: '',
      vendor2: 'SIAM OHGITANI\n2108146',
      unitPrice2: null,
      status: 'Waiting Quotation'
    },
    {
      id: 4,
      no: 4,
      partName: 'DISTILLATION COIL',
      spec: 'COIL-200L\n(OUTSIDE)\n/FVH4-3856V2CV',
      position: '',
      makerName: 'CLEANVY',
      qty: 3,
      unit: 'PCS',
      poRef: '2108146/22222ZS\n(Ref.po:G33603A)',
      remark: 'Ref.Last price for issue',
      isUrgent: true,
      attachments: [],
      machineModel: 'HGG12644N\n/ PMM F-1\n/ DEFECT',
      machineMaker: 'Cleanvy#02',
      serialNo: 'A06-026',
      acCode: '',
      vendor: 'IPO',
      unitPrice: null,
      currency: '',
      crCode: '',
      quotationNo: 'WAIT',
      quotationPdf: undefined,
      leadTime: '',
      vendor2: 'SIAM OHGITANI\n2108146',
      unitPrice2: null,
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

  editRow(item: RequisitionItem, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    // Store backup copy of current values in case user cancels
    item.backupData = JSON.parse(JSON.stringify(item));
    item.isEditing = true;
    this.showToast(`กำลังแก้ไขรายการ #${item.no}`);
  }

  saveRow(item: RequisitionItem, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    item.isEditing = false;
    delete item.backupData;
    this.showToast(`บันทึกข้อมูลรายการ #${item.no} เรียบร้อยแล้ว`);
  }

  cancelEditRow(item: RequisitionItem, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    if (item.backupData) {
      const backup = item.backupData;
      Object.assign(item, backup);
      delete item.backupData;
    }
    item.isEditing = false;
    this.showToast(`ยกเลิกการแก้ไขรายการ #${item.no}`);
  }

  addNewItem(): void {
    this.addRow();
  }

  addRow(): void {
    const nextNo = this.items.length + 1;
    const newItem: RequisitionItem = {
      id: Date.now(),
      no: nextNo,
      partName: '',
      spec: '',
      position: '',
      makerName: '',
      qty: 1,
      unit: 'PCS',
      remark: '',
      poRef: '',
      isUrgent: false,
      attachments: [],
      machineModel: '',
      machineMaker: '',
      serialNo: '',
      acCode: '',
      vendor: '',
      unitPrice: null,
      currency: 'BT',
      crCode: '',
      quotationNo: 'WAIT',
      leadTime: '',
      vendor2: '',
      unitPrice2: null,
      status: 'Waiting Quotation',
      isEditing: true
    };
    this.items.push(newItem);
    this.showToast(`เพิ่มรายการใหม่ #${nextNo} พร้อมแก้ไข`);
  }

  deleteItem(index: number, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    const removedNo = this.items[index]?.no;
    this.items.splice(index, 1);
    this.items.forEach((item, idx) => item.no = idx + 1);
    this.showToast(`ลบรายการ #${removedNo} แล้ว`);
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

  // OTP Login Methods (Single State - Zero Double-Type Bug)
  onCodeChange(val: string): void {
    const cleaned = (val || '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 5);
    this.otpCode = cleaned;
    this.loginError = '';

    const input = document.getElementById('master-otp-input') as HTMLInputElement;
    if (input && input.value !== cleaned) {
      input.value = cleaned;
    }

    if (this.otpCode.length === 5) {
      setTimeout(() => this.submitLogin(), 180);
    }
  }

  focusInput(): void {
    setTimeout(() => {
      const input = document.getElementById('master-otp-input') as HTMLInputElement;
      input?.focus();
    }, 10);
  }

  clearOtp(): void {
    this.otpCode = '';
    this.loginError = '';
    const input = document.getElementById('master-otp-input') as HTMLInputElement;
    if (input) input.value = '';
    this.focusInput();
  }

  setDemoCode(code: string): void {
    this.otpCode = code;
    const input = document.getElementById('master-otp-input') as HTMLInputElement;
    if (input) input.value = code;
    this.submitLogin();
  }

  async submitLogin(): Promise<void> {
    if (this.otpCode.length < 4) {
      this.loginError = 'Please enter a valid Employee ID (4-5 characters).';
      return;
    }

    if (this.loginPhase !== 'input') {
      return;
    }

    this.loginError = '';
    const candidateCode = this.otpCode;

    // 1. Immediately start rotating animation for instant UI feedback
    this.loginPhase = 'rotating';
    console.log(`%c[Suppier Auth] 🚀 Initiating verification for: ${candidateCode}`, 'color: #2563eb; font-weight: bold;');

    try {
      // 2. Query backend API connected to [Suppier].[dbo].[Master_Employee]
      const res = await this.apiService.verifyEmployee(candidateCode);

      if (res && res.success && res.user) {
        const user = res.user;
        console.log(`%c[Suppier Auth] ✅ Verification SUCCESS:`, 'color: #059669; font-weight: bold;', user);

        // Store user and update document detail fields (Request by, Division, Section)
        this.currentUser = user;
        this.loggedInEmployeeId = user.empNo;
        this.requestBy = user.fullName;
        if (user.division) this.division = user.division;
        if (user.section) this.section = user.section;

        // Progress smoothly through the animations
        setTimeout(() => {
          this.loginPhase = 'converging';
        }, 1200);

        setTimeout(() => {
          this.loginPhase = 'downloading';
          this.animateDownloadProgress();
        }, 1850);

        setTimeout(() => {
          this.loginPhase = 'success';
        }, 3300);

        setTimeout(() => {
          this.isLoggedIn = true;
          this.loginPhase = 'input';
          this.downloadPercent = 0;
          this.showToast(`Login successful. Welcome, ${this.requestBy} (${this.loggedInEmployeeId})`);
        }, 3900);

      } else {
        console.warn(`%c[Suppier Auth] ❌ Verification FAILED for: ${candidateCode}`, 'color: #dc2626; font-weight: bold;', res);
        this.handleLoginFailure(candidateCode, res?.message || `Invalid Employee ID "${candidateCode}". Please try again.`);
      }

    } catch (err: any) {
      console.error(`%c[Suppier Auth] 💥 Unexpected error during login:`, 'color: #dc2626;', err);
      this.handleLoginFailure(candidateCode, 'Failed to connect to authentication service.');
    }
  }

  private handleLoginFailure(failedCode: string, errorMsg: string): void {
    // 1. Rotate and turn red with warning vibration
    setTimeout(() => {
      this.loginPhase = 'fail-converging';
    }, 800);

    // 2. Shatter into pieces
    setTimeout(() => {
      this.loginPhase = 'shattered';
    }, 1500);

    // 3. Reset back to input
    setTimeout(() => {
      this.loginPhase = 'input';
      this.loginError = errorMsg || `Invalid Employee ID "${failedCode}". Please try again.`;
      this.clearOtp();
    }, 3300);
  }

  animateDownloadProgress(): void {
    this.downloadPercent = 18;
    const timer = setInterval(() => {
      if (this.downloadPercent < 96) {
        this.downloadPercent += Math.floor(Math.random() * 18) + 12;
        if (this.downloadPercent > 100) this.downloadPercent = 100;
      } else {
        this.downloadPercent = 100;
        clearInterval(timer);
      }
    }, 120);
  }

  logout(): void {
    console.log(`%c[Suppier Auth] 🚪 User ${this.loggedInEmployeeId} logged out.`, 'color: #64748b;');
    this.isLoggedIn = false;
    this.otpCode = '';
    this.loggedInEmployeeId = '';
    this.currentUser = null;
    this.loginPhase = 'input';
    this.downloadPercent = 0;
    this.showToast('Logged out successfully.');
    this.focusInput();
  }

}
