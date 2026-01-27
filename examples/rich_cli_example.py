from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from rich.console import Console
import sys

console = Console()
style = Style.from_dict({
    'prompt': '#00aa00 bold',
})

console.print("计算器启动 (Ctrl+C 或 Ctrl+D 退出)", style="dim")

try:
    while True: 
        # 打印分隔线
        print("─" * 80)
        
        # 获取用户输入
        expression = prompt('❯ ', style=style).strip()
        
        if not expression:
            # 如果是空输入，清除分隔线和提示符
            sys.stdout.write('\033[A\033[K')  # 上移一行并清除
            sys.stdout. write('\033[A\033[K')  # 再上移一行清除分隔线
            sys.stdout.flush()
            continue
        
        # 清除提示符那一行（向上移动并清除）
        sys.stdout.write('\033[A\033[K')
        sys.stdout.flush()
        
        # 清除分隔线
        sys.stdout.write('\033[A\033[K')
        sys.stdout.flush()
        
        # 显示表达式
        console.print(f"[cyan]>[/cyan] {expression}")
        
        # 计算结果
        try:
            result = eval(expression)
            console.print(f"[green]<[/green] {result}")
        except Exception as e: 
            console.print(f"[red]<[/red] Error: {e}")
        
except (KeyboardInterrupt, EOFError):
    console.print("\n[dim]再见![/dim]")