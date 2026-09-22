import { Injectable } from '@angular/core';

export interface EmployeeUser {
  empNo: string;
  fullName: string;
  rawName?: string;
  division: string;
  divisionName?: string;
  section: string;
  sectionName?: string;
  process?: string;
  positionGroup?: string;
  shiftGroup?: string;
  profilePictureUrl?: string;
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
    const code = (employeeId || '').trim().toUpperCase();
    console.log(`%c[Suppier API] 📡 Sending employee verification for "${code}" to ${this.baseUrl}/auth/verify-employee`, 'color: #2563eb; font-weight: bold;');

    try {
      const response = await fetch(`${this.baseUrl}/auth/verify-employee`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ employeeId: code })
      });

      const data = await response.json();
      console.log(`%c[Suppier API] 📥 Received response from Backend (Status: ${response.status}):`, 'color: #059669; font-weight: bold;', data);
      return data;
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
            rawName: 'MR.  DANUPHON  SUTTHIWATTHANAK',
            division: 'MA',
            divisionName: 'MECHANICAL ASS\'Y',
            section: 'M/M',
            sectionName: 'MACHINE MAINTENANCE',
            process: 'HEAT TREATMENT',
            positionGroup: 'TECH',
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
            rawName: 'MISS ARUNEE  CHANCHAY',
            division: 'GM',
            divisionName: 'G/M',
            section: 'MACHINING',
            sectionName: 'MACHINING',
            process: 'BIG CLEAN',
            positionGroup: 'OPT'
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
   * Fetch all requisition items from Database
   */
  async getRequisitionItems(): Promise<any[]> {
    console.log(`%c[Suppier API] 📡 Fetching requisition items...`, 'color: #2563eb;');
    try {
      const response = await fetch(`${this.baseUrl}/requisition/items`);
      const result = await response.json();
      console.log(`%c[Suppier API] 📥 Requisition items loaded:`, 'color: #059669;', result);
      return result.data || [];
    } catch (err) {
      console.warn('%c[Suppier API] ⚠️ Backend API offline, using local requisition data:', 'color: #d97706;', err);
      return [];
    }
  }

  /**
   * Save or update requisition item
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
}
