import { Injectable } from '@angular/core';

export interface EmployeeUser {
  empNo: string;
  fullName: string;
  titleName?: string;
  rawName?: string;
  thaiName?: string;
  division: string;
  divisionName?: string;
  section: string;
  sectionName?: string;
  process?: string;
  processName?: string;
  process_name?: string;
  positionGroup?: string;
  shiftGroup?: string;
  profilePictureUrl?: string;
  empDate?: string;
  deletedAt?: string | null;
}

export interface VerifyEmployeeResponse {
  success: boolean;
  message: string;
  user?: EmployeeUser;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:5000/api';

  /**
   * Verify employee ID from [Suppier].[dbo].[Master_Employee] via Backend API
   */
  async verifyEmployee(employeeId: string): Promise<VerifyEmployeeResponse> {
    const code = employeeId.trim().toUpperCase();
    console.log(`%c[Suppier API] 📡 Requesting auth verification for "${code}"...`, 'color: #2563eb; font-weight: bold;');

    try {
      const response = await fetch(`${this.baseUrl}/auth/verify-employee`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ employeeId: code })
      });

      const result = await response.json();
      console.log(`%c[Suppier API] 📥 Server Response:`, 'color: #059669;', result);
      return result;
    } catch (err) {
      console.warn('%c[Suppier API] ⚠️ Backend API offline or unreachable. Using fallback:', 'color: #d97706;', err);
      
      // Standalone Fallback for Danuphon and common test accounts
      if (code === 'X4770') {
        return {
          success: true,
          message: 'เข้าสู่ระบบสำเร็จ (Fallback Mode)',
          user: {
            empNo: 'X4770',
            fullName: 'DANUPHON SUTTHIWATTHANAK',
            titleName: 'MR. DANUPHON SUTTHIWATTHANAK',
            rawName: 'ดนุพล สุทธิวัฒนกุล',
            thaiName: 'ดนุพล สุทธิวัฒนกุล',
            division: 'MA',
            divisionName: 'MECHANICAL ASS\'Y',
            section: 'M/M',
            sectionName: 'MACHINE MAINTENANCE',
            process: 'HEAT TREATMENT',
            positionGroup: 'TECHNICIAN',
            profilePictureUrl: 'http://pbp083.bp.minebea.local:90/EmployeePicMA/X4770.jpg'
          }
        };
      }

      if (code === 'A3415') {
        return {
          success: true,
          message: 'เข้าสู่ระบบสำเร็จ (Fallback Mode)',
          user: {
            empNo: 'A3415',
            fullName: 'ARUNEE CHANCHAY',
            titleName: 'MISS ARUNEE CHANCHAY',
            rawName: 'อรุณี จันทร์ฉาย',
            thaiName: 'อรุณี จันทร์ฉาย',
            division: 'GM',
            divisionName: 'G/M',
            section: 'MC',
            sectionName: 'MACHINING',
            process: 'BIG CLEAN',
            positionGroup: 'OPERATOR',
            profilePictureUrl: 'http://pbp083.bp.minebea.local:90/EmployeePicPMC/A3415.jpg'
          }
        };
      }

      if (code === 'TK212') {
        return {
          success: true,
          message: 'เข้าสู่ระบบสำเร็จ (Fallback Mode)',
          user: {
            empNo: 'TK212',
            fullName: 'NUEAFA PONGPROM',
            titleName: 'MR. NUEAFA PONGPROM',
            rawName: 'เหนือฟ้า พงษ์พรหม',
            thaiName: 'เหนือฟ้า พงษ์พรหม',
            division: 'GM',
            divisionName: 'G/M',
            section: 'C/R',
            sectionName: 'COST REDUCTION',
            process: 'OFFICE CLERK',
            positionGroup: 'STAFF',
            profilePictureUrl: 'http://pbp083.bp.minebea.local:90/EmployeePicGM/TK212.jpg'
          }
        };
      }

      if (code === 'AB326') {
        return {
          success: true,
          message: 'เข้าสู่ระบบสำเร็จ (Fallback Mode)',
          user: {
            empNo: 'AB326',
            fullName: 'TEERAYUT NEUEGAEW',
            titleName: 'MR. TEERAYUT NEUEGAEW',
            rawName: 'MR. TEERAYUT NEUEGAEW',
            thaiName: '',
            division: 'MA',
            divisionName: 'MECHANICAL ASS\'Y',
            section: 'ASSY',
            sectionName: 'ASSEMBLY',
            process: 'PRODUCTION SET UP',
            positionGroup: 'TECHNICIAN',
            profilePictureUrl: 'http://pbp083.bp.minebea.local:90/EmployeePicMA/AB326.jpg'
          }
        };
      }

      if (code === '6284B') {
        return {
          success: true,
          message: 'เข้าสู่ระบบสำเร็จ (Fallback Mode)',
          user: {
            empNo: '6284B',
            fullName: 'RAWIPAT KHIANOAKSORN',
            titleName: 'MR. RAWIPAT KHIANOAKSORN',
            rawName: 'รวิภาส เขียนอักษร',
            thaiName: 'รวิภาส เขียนอักษร',
            division: 'MA',
            divisionName: 'MECHANICAL ASS\'Y',
            section: 'M/M',
            sectionName: 'MACHINE MAINTENANCE',
            process: 'STUDENT TRAINEE',
            positionGroup: 'STUDENT TRAINEE',
            profilePictureUrl: ''
          }
        };
      }

      return {
        success: false,
        message: `ไม่สามารถเชื่อมต่อ Backend API ได้ และไม่พบข้อมูลรหัส "${code}"`
      };
    }
  }

  /**
   * Fetch requisition document for a specific employee account
   */
  async getRequisitionDocumentForAccount(empNo: string): Promise<{ header: any; items: any[] } | null> {
    console.log(`%c[Suppier API] 📡 Fetching requisition document for account "${empNo}"...`, 'color: #2563eb;');
    try {
      const response = await fetch(`${this.baseUrl}/requisition/account/${encodeURIComponent(empNo)}`);
      const result = await response.json();
      if (result.success && result.data) {
        console.log(`%c[Suppier API] 📥 Account requisition document loaded:`, 'color: #059669;', result.data);
        return result.data;
      }
      return null;
    } catch (err) {
      console.warn('%c[Suppier API] ⚠️ Backend API offline, using fallback:', 'color: #d97706;', err);
      return null;
    }
  }

  /**
   * Fetch entire requisition document (Header & Items) from Database by docNumber
   */
  async getRequisitionDocument(docNumber = 'DOC-2026-0901-003'): Promise<{ header: any; items: any[] } | null> {
    console.log(`%c[Suppier API] 📡 Fetching requisition document "${docNumber}"...`, 'color: #2563eb;');
    try {
      const response = await fetch(`${this.baseUrl}/requisition/document/${docNumber}`);
      const result = await response.json();
      if (result.success && result.data) {
        console.log(`%c[Suppier API] 📥 Requisition document loaded:`, 'color: #059669;', result.data);
        return result.data;
      }
      return null;
    } catch (err) {
      console.warn('%c[Suppier API] ⚠️ Backend API offline, using fallback:', 'color: #d97706;', err);
      return null;
    }
  }

  /**
   * Save or update requisition header in Database
   */
  async saveRequisitionHeader(docNumber: string, header: any, empNo?: string): Promise<boolean> {
    console.log(`%c[Suppier API] 📡 Saving requisition header for "${docNumber}" (Emp: ${empNo || ''})...`, 'color: #2563eb;', header);
    try {
      const response = await fetch(`${this.baseUrl}/requisition/document/${docNumber}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...header, empNo })
      });
      const res = await response.json();
      console.log(`%c[Suppier API] 📥 Save header response:`, 'color: #059669;', res);
      return !!res.success;
    } catch (err) {
      console.error('%c[Suppier API] ❌ Failed to save header to backend:', 'color: #dc2626;', err);
      return false;
    }
  }

  /**
   * Save entire document (Header + All Items) in a single transactional request for the account
   */
  async saveEntireDocument(docNumber: string, header: any, items: any[], empNo?: string): Promise<boolean> {
    console.log(`%c[Suppier API] 📡 Saving entire requisition document "${docNumber}" for account "${empNo || ''}"...`, 'color: #2563eb;', { header, itemsCount: items.length });
    try {
      const response = await fetch(`${this.baseUrl}/requisition/save-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          header: { ...header, docNumber, empNo },
          items,
          empNo
        })
      });
      const res = await response.json();
      console.log(`%c[Suppier API] 📥 Save-all response:`, 'color: #059669;', res);
      return !!res.success;
    } catch (err) {
      console.error('%c[Suppier API] ❌ Failed to save entire document to backend:', 'color: #dc2626;', err);
      return false;
    }
  }

  /**
   * Fetch all requisition items from Database
   */
  async getRequisitionItems(docNumber = 'DOC-2026-0901-003'): Promise<any[]> {
    console.log(`%c[Suppier API] 📡 Fetching requisition items...`, 'color: #2563eb;');
    try {
      const response = await fetch(`${this.baseUrl}/requisition/items?docNumber=${encodeURIComponent(docNumber)}`);
      const result = await response.json();
      console.log(`%c[Suppier API] 📥 Requisition items loaded:`, 'color: #059669;', result);
      return result.data || [];
    } catch (err) {
      console.warn('%c[Suppier API] ⚠️ Backend API offline, using local requisition data:', 'color: #d97706;', err);
      return [];
    }
  }

  /**
   * Save or update single requisition item
   */
  async saveRequisitionItem(item: any): Promise<boolean> {
    console.log(`%c[Suppier API] 📡 Saving requisition item:`, 'color: #2563eb;', item);
    try {
      const url = item.id ? `${this.baseUrl}/requisition/items/${item.id}` : `${this.baseUrl}/requisition/items`;
      const method = item.id ? 'PUT' : 'POST';
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      });
      const res = await response.json();
      console.log(`%c[Suppier API] 📥 Save item response:`, 'color: #059669;', res);
      return !!res.success;
    } catch (err) {
      console.error('%c[Suppier API] ❌ Failed to save requisition item to backend:', 'color: #dc2626;', err);
      return false;
    }
  }

  /**
   * Delete requisition item from database
   */
  async deleteRequisitionItem(id: number): Promise<boolean> {
    console.log(`%c[Suppier API] 📡 Deleting requisition item #${id}...`, 'color: #2563eb;');
    try {
      const response = await fetch(`${this.baseUrl}/requisition/items/${id}`, {
        method: 'DELETE'
      });
      const res = await response.json();
      return !!res.success;
    } catch (err) {
      console.error('%c[Suppier API] ❌ Failed to delete item:', 'color: #dc2626;', err);
      return false;
    }
  }

  /**
   * Get all quotation requests submitted by users (for PURCHASE section view)
   */
  async getAllQuotationRequests(): Promise<Array<{ header: any; items: any[] }>> {
    console.log(`%c[Suppier API] 📡 Fetching all user quotation requests...`, 'color: #2563eb;');
    try {
      const response = await fetch(`${this.baseUrl}/requisition/all-requests`);
      const res = await response.json();
      if (res.success && Array.isArray(res.data)) {
        console.log(`%c[Suppier API] 📥 Loaded ${res.data.length} quotation requests:`, 'color: #059669;', res.data);
        return res.data;
      }
    } catch (err) {
      console.warn('%c[Suppier API] ⚠️ Failed to fetch all requests from backend:', 'color: #d97706;', err);
    }
    return [];
  }
}
