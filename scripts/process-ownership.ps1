. (Join-Path $PSScriptRoot "common.ps1")

if ($null -eq ('TossDashboard.PhaseOne.KillOnCloseJob' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using Microsoft.Win32.SafeHandles;

namespace TossDashboard.PhaseOne
{
    public sealed class KillOnCloseJob : IDisposable
    {
        private const uint JobObjectLimitKillOnJobClose = 0x00002000;
        private const uint CreateSuspended = 0x00000004;
        private const uint ExtendedStartupInfoPresent = 0x00080000;
        private const uint CreateNoWindow = 0x08000000;
        private const int ErrorInsufficientBuffer = 122;
        private const long ProcThreadAttributeJobList = 0x0002000d;
        private const uint ResumeThreadFailed = 0xffffffff;
        private const uint WaitObject0 = 0x00000000;
        private const uint WaitTimeout = 0x00000102;
        private const uint WaitFailed = 0xffffffff;
        private SafeFileHandle handle;
        private bool disposed;

        public KillOnCloseJob()
        {
            handle = NativeMethods.CreateJobObject(IntPtr.Zero, null);
            if (handle == null || handle.IsInvalid)
            {
                throw new Win32Exception(Marshal.GetLastWin32Error(), "CreateJobObject failed.");
            }

            var information = new JobObjectExtendedLimitInformation();
            information.BasicLimitInformation.LimitFlags = JobObjectLimitKillOnJobClose;
            int length = Marshal.SizeOf<JobObjectExtendedLimitInformation>();
            IntPtr buffer = Marshal.AllocHGlobal(length);
            try
            {
                Marshal.StructureToPtr(information, buffer, false);
                if (!NativeMethods.SetInformationJobObject(handle, 9, buffer, (uint)length))
                {
                    throw new Win32Exception(
                        Marshal.GetLastWin32Error(),
                        "SetInformationJobObject failed."
                    );
                }
            }
            catch
            {
                handle.Dispose();
                throw;
            }
            finally
            {
                Marshal.FreeHGlobal(buffer);
            }
        }

        public Process StartSuspended(
            string applicationPath,
            string[] arguments,
            string workingDirectory
        )
        {
            return StartAtomicallyAssigned(
                applicationPath,
                arguments,
                workingDirectory,
                true
            );
        }

        public Process StartAssignedSuspendedForCanary(
            string applicationPath,
            string[] arguments,
            string workingDirectory
        )
        {
            return StartAtomicallyAssigned(
                applicationPath,
                arguments,
                workingDirectory,
                false
            );
        }

        private Process StartAtomicallyAssigned(
            string applicationPath,
            string[] arguments,
            string workingDirectory,
            bool resumePrimaryThread
        )
        {
            ThrowIfDisposed();
            if (String.IsNullOrWhiteSpace(applicationPath))
            {
                throw new ArgumentException("An application path is required.", nameof(applicationPath));
            }
            if (arguments == null)
            {
                throw new ArgumentNullException(nameof(arguments));
            }
            if (String.IsNullOrWhiteSpace(workingDirectory))
            {
                throw new ArgumentException("A working directory is required.", nameof(workingDirectory));
            }

            var commandLine = new StringBuilder(QuoteWindowsArgument(applicationPath));
            foreach (string argument in arguments)
            {
                commandLine.Append(' ');
                commandLine.Append(QuoteWindowsArgument(argument));
            }
            if (commandLine.Length >= 32767)
            {
                throw new ArgumentException("The suspended process command line is too long.");
            }

            ProcessInformation processInformation = new ProcessInformation();
            IntPtr attributeList = IntPtr.Zero;
            IntPtr jobHandleValue = IntPtr.Zero;
            bool attributeListInitialized = false;
            bool jobHandleReferenceAdded = false;
            SafeFileHandle jobHandle = handle;
            try
            {
                IntPtr attributeListSize = IntPtr.Zero;
                bool sizeProbeSucceeded = NativeMethods.InitializeProcThreadAttributeList(
                    IntPtr.Zero,
                    1,
                    0,
                    ref attributeListSize
                );
                int sizeProbeError = Marshal.GetLastWin32Error();
                if (
                    sizeProbeSucceeded ||
                    sizeProbeError != ErrorInsufficientBuffer ||
                    attributeListSize == IntPtr.Zero
                )
                {
                    throw new Win32Exception(
                        sizeProbeError,
                        "Unable to size the atomic process Job attribute list."
                    );
                }

                attributeList = Marshal.AllocHGlobal(attributeListSize);
                if (!NativeMethods.InitializeProcThreadAttributeList(
                        attributeList,
                        1,
                        0,
                        ref attributeListSize
                    ))
                {
                    throw new Win32Exception(
                        Marshal.GetLastWin32Error(),
                        "Unable to initialize the atomic process Job attribute list."
                    );
                }
                attributeListInitialized = true;

                jobHandleValue = Marshal.AllocHGlobal(IntPtr.Size);
                jobHandle.DangerousAddRef(ref jobHandleReferenceAdded);
                Marshal.WriteIntPtr(jobHandleValue, jobHandle.DangerousGetHandle());
                if (!NativeMethods.UpdateProcThreadAttribute(
                        attributeList,
                        0,
                        new IntPtr(ProcThreadAttributeJobList),
                        jobHandleValue,
                        new IntPtr(IntPtr.Size),
                        IntPtr.Zero,
                        IntPtr.Zero
                    ))
                {
                    throw new Win32Exception(
                        Marshal.GetLastWin32Error(),
                        "Unable to configure atomic process Job association."
                    );
                }

                var startupInfo = new StartupInfoEx();
                startupInfo.StartupInfo.Size = (uint)Marshal.SizeOf<StartupInfoEx>();
                startupInfo.AttributeList = attributeList;
                if (!NativeMethods.CreateProcess(
                        applicationPath,
                        commandLine,
                        IntPtr.Zero,
                        IntPtr.Zero,
                        false,
                        CreateSuspended | CreateNoWindow | ExtendedStartupInfoPresent,
                        IntPtr.Zero,
                        workingDirectory,
                        ref startupInfo,
                        out processInformation
                    ))
                {
                    throw new Win32Exception(
                        Marshal.GetLastWin32Error(),
                        "CreateProcessW with atomic Job association failed."
                    );
                }
            }
            finally
            {
                if (attributeListInitialized)
                {
                    NativeMethods.DeleteProcThreadAttributeList(attributeList);
                }
                if (jobHandleValue != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(jobHandleValue);
                }
                if (attributeList != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(attributeList);
                }
                if (jobHandleReferenceAdded)
                {
                    jobHandle.DangerousRelease();
                }
            }

            Process process = null;
            bool processHandedOff = false;
            try
            {
                process = Process.GetProcessById((int)processInformation.ProcessId);
                IntPtr managedIdentityHandle = process.Handle;
                if (managedIdentityHandle == IntPtr.Zero)
                {
                    throw new InvalidOperationException("Unable to retain the suspended process identity.");
                }
                if (
                    resumePrimaryThread &&
                    NativeMethods.ResumeThread(processInformation.ThreadHandle) == ResumeThreadFailed
                )
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error(), "ResumeThread failed.");
                }
                processHandedOff = true;
                return process;
            }
            finally
            {
                try
                {
                    if (!processHandedOff)
                    {
                        try
                        {
                            TerminateCreatedProcessAndWait(processInformation.ProcessHandle);
                        }
                        finally
                        {
                            if (process != null)
                            {
                                process.Dispose();
                            }
                        }
                    }
                }
                finally
                {
                    NativeMethods.CloseHandle(processInformation.ThreadHandle);
                    NativeMethods.CloseHandle(processInformation.ProcessHandle);
                }
            }
        }

        private static void TerminateCreatedProcessAndWait(IntPtr processHandle)
        {
            if (!NativeMethods.TerminateProcess(processHandle, 1))
            {
                int terminationError = Marshal.GetLastWin32Error();
                uint immediateState = NativeMethods.WaitForSingleObject(processHandle, 0);
                if (immediateState != WaitObject0)
                {
                    throw new Win32Exception(
                        terminationError,
                        "Unable to terminate a failed atomically assigned process."
                    );
                }
                return;
            }

            uint waitResult = NativeMethods.WaitForSingleObject(processHandle, 10000);
            if (waitResult == WaitObject0)
            {
                return;
            }
            if (waitResult == WaitTimeout)
            {
                throw new TimeoutException(
                    "A failed atomically assigned process did not terminate in time."
                );
            }
            if (waitResult == WaitFailed)
            {
                throw new Win32Exception(
                    Marshal.GetLastWin32Error(),
                    "Waiting for a failed atomically assigned process failed."
                );
            }
            throw new InvalidOperationException(
                "Waiting for a failed atomically assigned process returned an unexpected result."
            );
        }

        public void TerminateAndWait(int timeoutMilliseconds)
        {
            ThrowIfDisposed();
            if (timeoutMilliseconds < 0)
            {
                throw new ArgumentOutOfRangeException(nameof(timeoutMilliseconds));
            }
            if (!NativeMethods.TerminateJobObject(handle, 1))
            {
                throw new Win32Exception(
                    Marshal.GetLastWin32Error(),
                    "TerminateJobObject failed."
                );
            }

            var stopwatch = Stopwatch.StartNew();
            while (true)
            {
                JobObjectBasicAccountingInformation accounting;
                uint returnedLength;
                if (!NativeMethods.QueryInformationJobObject(
                        handle,
                        1,
                        out accounting,
                        (uint)Marshal.SizeOf<JobObjectBasicAccountingInformation>(),
                        out returnedLength
                    ))
                {
                    throw new Win32Exception(
                        Marshal.GetLastWin32Error(),
                        "QueryInformationJobObject failed."
                    );
                }
                if (accounting.ActiveProcesses == 0)
                {
                    return;
                }
                if (stopwatch.ElapsedMilliseconds >= timeoutMilliseconds)
                {
                    throw new TimeoutException("Owned job processes did not terminate in time.");
                }
                Thread.Sleep(25);
            }
        }

        public void Dispose()
        {
            if (disposed)
            {
                return;
            }
            disposed = true;
            if (handle != null)
            {
                handle.Dispose();
                handle = null;
            }
        }

        private void ThrowIfDisposed()
        {
            if (disposed)
            {
                throw new ObjectDisposedException(nameof(KillOnCloseJob));
            }
        }

        private static string QuoteWindowsArgument(string argument)
        {
            if (argument == null)
            {
                throw new ArgumentNullException(nameof(argument));
            }
            if (argument.Length > 0 && argument.IndexOfAny(
                    new[] { ' ', '\t', '\r', '\n', '\v', '"' }
                ) < 0)
            {
                return argument;
            }

            var quoted = new StringBuilder();
            quoted.Append('"');
            int backslashes = 0;
            foreach (char character in argument)
            {
                if (character == '\\')
                {
                    backslashes += 1;
                    continue;
                }
                if (character == '"')
                {
                    quoted.Append('\\', (backslashes * 2) + 1);
                    quoted.Append('"');
                    backslashes = 0;
                    continue;
                }
                quoted.Append('\\', backslashes);
                backslashes = 0;
                quoted.Append(character);
            }
            quoted.Append('\\', backslashes * 2);
            quoted.Append('"');
            return quoted.ToString();
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JobObjectBasicLimitInformation
        {
            public long PerProcessUserTimeLimit;
            public long PerJobUserTimeLimit;
            public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize;
            public UIntPtr MaximumWorkingSetSize;
            public uint ActiveProcessLimit;
            public UIntPtr Affinity;
            public uint PriorityClass;
            public uint SchedulingClass;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct IoCounters
        {
            public ulong ReadOperationCount;
            public ulong WriteOperationCount;
            public ulong OtherOperationCount;
            public ulong ReadTransferCount;
            public ulong WriteTransferCount;
            public ulong OtherTransferCount;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JobObjectExtendedLimitInformation
        {
            public JobObjectBasicLimitInformation BasicLimitInformation;
            public IoCounters IoInfo;
            public UIntPtr ProcessMemoryLimit;
            public UIntPtr JobMemoryLimit;
            public UIntPtr PeakProcessMemoryUsed;
            public UIntPtr PeakJobMemoryUsed;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JobObjectBasicAccountingInformation
        {
            public long TotalUserTime;
            public long TotalKernelTime;
            public long ThisPeriodTotalUserTime;
            public long ThisPeriodTotalKernelTime;
            public uint TotalPageFaultCount;
            public uint TotalProcesses;
            public uint ActiveProcesses;
            public uint TotalTerminatedProcesses;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct StartupInfo
        {
            public uint Size;
            public IntPtr Reserved;
            public IntPtr Desktop;
            public IntPtr Title;
            public uint X;
            public uint Y;
            public uint XSize;
            public uint YSize;
            public uint XCountChars;
            public uint YCountChars;
            public uint FillAttribute;
            public uint Flags;
            public ushort ShowWindow;
            public ushort ReservedSize;
            public IntPtr ReservedBytes;
            public IntPtr StandardInput;
            public IntPtr StandardOutput;
            public IntPtr StandardError;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct StartupInfoEx
        {
            public StartupInfo StartupInfo;
            public IntPtr AttributeList;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct ProcessInformation
        {
            public IntPtr ProcessHandle;
            public IntPtr ThreadHandle;
            public uint ProcessId;
            public uint ThreadId;
        }

        private static class NativeMethods
        {
            [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
            internal static extern SafeFileHandle CreateJobObject(
                IntPtr jobAttributes,
                string name
            );

            [DllImport("kernel32.dll", SetLastError = true)]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool SetInformationJobObject(
                SafeFileHandle job,
                int informationClass,
                IntPtr information,
                uint informationLength
            );

            [DllImport("kernel32.dll", SetLastError = true)]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool InitializeProcThreadAttributeList(
                IntPtr attributeList,
                int attributeCount,
                int flags,
                ref IntPtr size
            );

            [DllImport("kernel32.dll", SetLastError = true)]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool UpdateProcThreadAttribute(
                IntPtr attributeList,
                uint flags,
                IntPtr attribute,
                IntPtr value,
                IntPtr size,
                IntPtr previousValue,
                IntPtr returnSize
            );

            [DllImport("kernel32.dll")]
            internal static extern void DeleteProcThreadAttributeList(
                IntPtr attributeList
            );

            [DllImport(
                "kernel32.dll",
                EntryPoint = "CreateProcessW",
                CharSet = CharSet.Unicode,
                SetLastError = true
            )]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool CreateProcess(
                string applicationName,
                StringBuilder commandLine,
                IntPtr processAttributes,
                IntPtr threadAttributes,
                [MarshalAs(UnmanagedType.Bool)] bool inheritHandles,
                uint creationFlags,
                IntPtr environment,
                string currentDirectory,
                ref StartupInfoEx startupInfo,
                out ProcessInformation processInformation
            );

            [DllImport("kernel32.dll", SetLastError = true)]
            internal static extern uint ResumeThread(IntPtr thread);

            [DllImport("kernel32.dll", SetLastError = true)]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool TerminateProcess(IntPtr process, uint exitCode);

            [DllImport("kernel32.dll", SetLastError = true)]
            internal static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);

            [DllImport("kernel32.dll", SetLastError = true)]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool CloseHandle(IntPtr handle);

            [DllImport("kernel32.dll", SetLastError = true)]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool TerminateJobObject(
                SafeFileHandle job,
                uint exitCode
            );

            [DllImport("kernel32.dll", SetLastError = true)]
            [return: MarshalAs(UnmanagedType.Bool)]
            internal static extern bool QueryInformationJobObject(
                SafeFileHandle job,
                int informationClass,
                out JobObjectBasicAccountingInformation information,
                uint informationLength,
                out uint returnLength
            );
        }
    }
}
'@
}

function Assert-OwnedProcessGroup {
    param([Parameter(Mandatory = $true)][object] $Group)

    if ($Group.PSObject.TypeNames -notcontains "PhaseOne.OwnedProcessGroup") {
        throw "An invalid owned process group was supplied."
    }
}

function New-OwnedProcessGroup {
    return [pscustomobject]@{
        PSTypeName = "PhaseOne.OwnedProcessGroup"
        Job = [TossDashboard.PhaseOne.KillOnCloseJob]::new()
        Processes = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
        IsStopped = $false
    }
}

function Start-OwnedProcess {
    param(
        [Parameter(Mandatory = $true)][object] $Group,
        [Parameter(Mandatory = $true)][ValidatePattern('^[a-z][a-z0-9-]{0,31}$')]
        [string] $Name,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $ArgumentList = @(),
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [Parameter(Mandatory = $true)][string] $TaskTempDirectory,
        [Parameter(Mandatory = $true)][string] $StandardOutputPath,
        [Parameter(Mandatory = $true)][string] $StandardErrorPath
    )

    Assert-OwnedProcessGroup -Group $Group
    if ($Group.IsStopped) {
        throw "Cannot start a process in a stopped owned process group."
    }
    if (-not $IsWindows) {
        throw "Phase 1 owned process groups require Windows."
    }

    $repoRoot = Get-RepoRoot
    $launcherPath = [System.IO.Path]::GetFullPath(
        (Join-Path $PSScriptRoot "owned-process-launcher.ps1")
    )
    if (-not (Test-Path -LiteralPath $launcherPath -PathType Leaf)) {
        throw "The owned-process launcher is missing."
    }
    Assert-SafeMutableRepositoryFile -Path $launcherPath

    $targetPath = [System.IO.Path]::GetFullPath($FilePath)
    if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
        throw "An owned process target is missing: $targetPath"
    }
    $workingPath = [System.IO.Path]::GetFullPath($WorkingDirectory)
    Assert-SafeRepositoryPath -Path $workingPath
    if (-not (Test-Path -LiteralPath $workingPath -PathType Container)) {
        throw "An owned process working directory is missing."
    }

    $taskTempPath = [System.IO.Path]::GetFullPath($TaskTempDirectory)
    $taskTempRoot = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot "var\tmp\phase-01")
    )
    $relativeTaskTemp = [System.IO.Path]::GetRelativePath($taskTempRoot, $taskTempPath)
    if ($relativeTaskTemp -cnotmatch '^[0-9a-f]{32}$') {
        throw "The owned process launch directory is outside the task temp root."
    }
    Assert-SafeRepositoryPath -Path $taskTempPath
    if (-not (Test-Path -LiteralPath $taskTempPath -PathType Container)) {
        throw "The owned process launch directory is missing."
    }

    $stdoutPath = [System.IO.Path]::GetFullPath($StandardOutputPath)
    $stderrPath = [System.IO.Path]::GetFullPath($StandardErrorPath)
    if ($stdoutPath -ceq $stderrPath) {
        throw "Owned process output and error paths must be different."
    }
    foreach ($logPath in @($stdoutPath, $stderrPath)) {
        Assert-SafeMutableRepositoryFile -Path $logPath
        [System.IO.File]::WriteAllText($logPath, "")
        Assert-SafeMutableRepositoryFile -Path $logPath
    }

    $launchId = [System.Guid]::NewGuid().ToString("N")
    $specificationPath = Join-Path $taskTempPath "owned-launch-$Name-$launchId.json"
    Assert-SafeMutableRepositoryFile -Path $specificationPath
    $specification = [ordered]@{
        schema_version = 2
        file_path = $targetPath
        working_directory = $workingPath
        argument_list = @($ArgumentList)
        standard_output_path = $stdoutPath
        standard_error_path = $stderrPath
    }
    $json = $specification | ConvertTo-Json -Compress -Depth 4
    $specificationBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json)
    $sha256Algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $specificationHash = [System.Convert]::ToHexString(
            $sha256Algorithm.ComputeHash($specificationBytes)
        ).ToLowerInvariant()
    }
    finally {
        $sha256Algorithm.Dispose()
    }
    [System.IO.File]::WriteAllBytes($specificationPath, $specificationBytes)
    Assert-SafeMutableRepositoryFile -Path $specificationPath

    $pwshCommand = Get-Command pwsh.exe -ErrorAction Stop
    $launcherArguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $launcherPath,
        "-LaunchSpecPath", $specificationPath,
        "-ExpectedSha256", $specificationHash
    )

    $process = $Group.Job.StartSuspended(
        $pwshCommand.Source,
        [string[]] $launcherArguments,
        $repoRoot
    )
    try {
        $Group.Processes.Add($process)
        return $process
    }
    catch {
        $process.Dispose()
        throw
    }
}

function Stop-OwnedProcessGroup {
    param(
        [Parameter(Mandatory = $true)][object] $Group,
        [int] $TimeoutMilliseconds = 10000
    )

    Assert-OwnedProcessGroup -Group $Group
    if ($Group.IsStopped) {
        return
    }

    $errors = [System.Collections.Generic.List[string]]::new()
    try {
        $Group.Job.TerminateAndWait($TimeoutMilliseconds)
    }
    catch {
        $errors.Add($_.Exception.Message)
    }
    finally {
        try {
            $Group.Job.Dispose()
        }
        catch {
            $errors.Add($_.Exception.Message)
        }
    }

    foreach ($process in $Group.Processes) {
        try {
            if (-not $process.WaitForExit($TimeoutMilliseconds)) {
                throw "An owned process launcher did not terminate in time."
            }
        }
        catch {
            $errors.Add($_.Exception.Message)
        }
        finally {
            $process.Dispose()
        }
    }
    $Group.IsStopped = $true
    if ($errors.Count -gt 0) {
        throw ($errors -join [Environment]::NewLine)
    }
}

function Test-ExactProcessIdentityAlive {
    param(
        [Parameter(Mandatory = $true)][int] $ProcessId,
        [Parameter(Mandatory = $true)][long] $StartTimeUtcTicks
    )

    try {
        $process = [System.Diagnostics.Process]::GetProcessById($ProcessId)
        try {
            # Pin the OS process handle before reading identity metadata so a
            # later PID reuse cannot change which process this object observes.
            $null = $process.Handle
            return $process.StartTime.ToUniversalTime().Ticks -eq $StartTimeUtcTicks
        }
        finally {
            $process.Dispose()
        }
    }
    catch [System.ArgumentException] {
        return $false
    }
    catch [System.InvalidOperationException] {
        return $false
    }
}

function Stop-ExactProcessIdentity {
    param(
        [Parameter(Mandatory = $true)][int] $ProcessId,
        [Parameter(Mandatory = $true)][long] $StartTimeUtcTicks,
        [switch] $IncludeDescendants
    )

    try {
        $process = [System.Diagnostics.Process]::GetProcessById($ProcessId)
    }
    catch [System.ArgumentException] {
        return
    }
    try {
        # GetProcessById alone retains only a numeric PID on current .NET.
        # Force a handle open before the identity comparison and reuse that
        # handle for HasExited/Kill/WaitForExit.
        $null = $process.Handle
        if ($process.StartTime.ToUniversalTime().Ticks -ne $StartTimeUtcTicks) {
            throw "Refusing to stop a reused process identifier."
        }
        if (-not $process.HasExited) {
            if ($IncludeDescendants) {
                $process.Kill($true)
            }
            else {
                $process.Kill()
            }
            if (-not $process.WaitForExit(10000)) {
                throw "An exact process identity did not terminate."
            }
        }
    }
    catch [System.InvalidOperationException] {
        return
    }
    finally {
        $process.Dispose()
    }
}
