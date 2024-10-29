import aiohttp 
import asyncio

async def stream_file(url, file_path, chunk_size=1024):
    async def file_generator(file_path, chunk_size):
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                yield chunk
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=file_generator(file_path, chunk_size)) as response:
            if response.status == 200:
                print("File streamed successfully!")
                print(await response.text())  
            else:
                print(f"Failed to stream file. Status: {response.status}")

def has_access(path):
    import pathlib 
    try:
        with pathlib.Path(path).open("rb") as f:
            pass
    except:
        return False 
    return True

async def upload_folder(folder_path):
    import pathlib 
    tasks = []
    print("Uploading",folder_path)
    for f in pathlib.Path(folder_path).glob("*"):
        print(f)
        if not f.is_file():
            continue
        if has_access(f.absolute()):
            tasks.append(asyncio.create_task(stream_file("http://localhost:7070/file/{}".format(f.name), f.absolute())))
    await asyncio.gather(*tasks)

async def upload_folders(folders):
    import pathlib
    tasks = []
    for folder in folders:
        for x in range(100):
            tasks.append(upload_folder(pathlib.Path(folder).absolute()))
    await asyncio.gather(*tasks)
def main():
   
   
   asyncio.run(upload_folders(["/home/retoor/projects/cpython/Include/", "/tmp","/var/log"]))