ERR_TEXT_NO_CEPH_ACCESS = """\
An error was encountered on your data request named [{0}] for user [{1}].
Cannot access Ceph Object Storage for Data Tiles. Please contact [{2}]."""

ERR_TEXT_NO_TOP_DIR = """\
An error was encountered on your data request named [{0}] for user [{1}].
No top level directory was found. Please forward this email to [{2}]"""

ERR_TEXT_TOPLEVEL_DIR_DUP = """\
An error was encountered on your data request named [{0}] for user [{1}].
A duplicate FTP request toplevel directory was found. Please wait
5 minutes in between submitting FTP requests and creating FTP folders.
If error still persists, forward this email to [{2}]""" 

ERR_TEXT_FAILED_CREATE_DATA_CLASS_DIR = """\
An error was encountered on your data request named [{0}] for user [{1}].
The system failed to create an dataclass subdirectory inside the FTP
folder at location [{2}]. Please forward this email to ({3})
so that we can address this issue.

---RESULT TRACE---

{4}"""

ERR_TEXT_FAILED_DOWNLOAD_TILES = """\
Cannot access Ceph Data Store. An error was encountered on your data request named [{0}] for user [{1}].
The system failed to download the following files: [{2}]. Either the file/s do/es not exist,
or the Ceph Data Storage is down. Please forward this email to ({3}) that we can address this issue..

---RESULT TRACE---

{4}"""

ERR_TEXT_FAILED_CREATE_FTP_DIR = """\
An error was encountered on your data request named [{0}] for user [{1}].
The system failed to create the FTP directory at location [{2}].
Please ensure that you are a legitimate user and have permission to use
this FTP service. If you are a legitimate user, please e-mail the system
administrator ({3}) regarding this error.

---RESULT TRACE---

{4}"""

ERR_TEXT_NO_USER_FOLDER = """\
An error was encountered on your data request named [{0}] for user [{1}].
No FTP folder was found for username [{1}]. Please ensure you have
access rights to the FTP repository. Otherwise, please contact the
system administrator ({2}) regarding this error."""

ERR_TEXT_GENERIC = """\
An unexpected error was encountered on your data request named [{0}] for user [{1}].
Please forward this mail to the system administrator ({2}).

---RESULT TRACE---

{3}"""

SUCCESS_TEXT = """\
Data request named [{0}] for user [{1}] has been succesfully processed.

With your LiPAD username and password, please login with an FTPES client
like Filezilla, to ftpes://ftp.dream.upd.edu.ph. Your requested datasets
will be in a new folder named [{0}] under the directory [DL/DAD/] and will be available for 30 days only due to infrastructure limitations.

FTP Server: ftpes://ftp.dream.upd.edu.ph/
Folder location: /mnt/FTP/Others/{1}/DL/DAD/lipad_requests/{0}
Encryption: Require explicit FTP over TLS
Logon Type: Normal
Username: {1}
Password: [your LiPAD password]

Please refer to the FTP access instructions [https://lipad.dream.upd.edu.ph/help/#download-ftp]
for further information. For issues encountered, please email {2}"""